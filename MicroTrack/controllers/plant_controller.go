package controllers

import (
	"MicroTrack/config"
	"MicroTrack/models"
	"context"
	"fmt"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo/options"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

var plantCollection *mongo.Collection

const MaxLimit int64 = 100

type PlantUpdateFields struct {
	Name           string    `bson:"name,omitempty"`
	GroupID        string    `bson:"group_id,omitempty"`
	ScientificName string    `bson:"scientific_name,omitempty"`
	GrowthDays     int       `bson:"growth_days,omitempty"`
	RecordedDate   time.Time `bson:"recorded_date,omitempty"`
	SeedingDate    time.Time `bson:"seeding_date,omitempty"`
	HarvestDate    time.Time `bson:"harvest_date,omitempty"`
	Description    string    `bson:"description,omitempty"`
	Height         float64   `bson:"height,omitempty"`
	LeafColor      string    `bson:"leaf_color,omitempty"`
	Floor          string    `bson:"floor,omitempty"`
	Humidity       float64   `bson:"humidity,omitempty"`
	Temperature    float64   `bson:"temperature,omitempty"`
	GrowthStage    string    `bson:"growth_stage,omitempty"`
}

type PlantInsertFields struct {
	PlantID        int       `bson:"plant_id"`
	GroupID        string    `bson:"group_id,omitempty"`
	Name           string    `bson:"name"`
	ScientificName string    `bson:"scientific_name"`
	Description    string    `bson:"description"`
	GrowthDays     int       `bson:"growth_days"`
	Height         float64   `bson:"height"`
	LeafColor      string    `bson:"leaf_color"`
	Floor          string    `bson:"floor"`
	Humidity       float64   `bson:"humidity"`
	Temperature    float64   `bson:"temperature"`
	SeedingDate    time.Time `json:"-" bson:"seeding_date"`
	RecordedDate   time.Time `bson:"recorded_date"`
	HarvestDate    time.Time `json:"-" bson:"harvest_date"`
	GrowthStage    string    `bson:"growth_stage"`
}

func InitPlantController() {
	if config.DB == nil {
		log.Fatal("❌ Database connection not initialized. Call ConnectDB() first.")
	}
	plantCollection = config.GetCollection("plants")
	fmt.Println("🌱 Plant Controller Initialized!")
}

// GetPlants godoc
// @Summary Get all plants
// @Description Get a list of all plants
// @Tags Public - Plants
// @Accept json
// @Produce json
// @Success 200 {object} []models.PlantListResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /plants [get]
func GetPlants(c *gin.Context) {
	cursor, err := plantCollection.Find(context.Background(), bson.M{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch plants"})
		return
	}
	defer cursor.Close(context.Background())

	var plants []models.Plant
	if err := cursor.All(context.Background(), &plants); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse plants"})
		return
	}

	c.JSON(http.StatusOK, plants)
	}


// AddPlant godoc
// @Summary Add a new plant
// @Description Create a new plant entry with details like name, seeding date, and harvesting date.
// @Tags Admin - Plants
// @Accept json
// @Produce json
// @Param plant body models.Plant true "Plant data"
// @Success 201 {object} models.Plant
// @Failure 400 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /plants [post]
// @Security BearerAuth
func AddPlant(c *gin.Context) {
	var plant models.Plant
	if err := c.BindJSON(&plant); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data"})
		return
	}

	if plant.GroupID == "" {
		plant.GroupID = primitive.NewObjectID().Hex()
	}

	now := time.Now()
	plant.RecordedDate = now
	plant.HarvestDate = plant.SeedingDate.Add(time.Hour * 24 * time.Duration(plant.GrowthDays))

	ctx := context.Background()
	opts := options.FindOne().SetSort(bson.D{{Key: "plant_id", Value: -1}})
	var lastPlant models.Plant
	err := plantCollection.FindOne(ctx, bson.D{}, opts).Decode(&lastPlant)
	if err != nil {
		plant.PlantID = 1
	} else {
		plant.PlantID = lastPlant.PlantID + 1
	}

	doc := PlantInsertFields{
		PlantID:        plant.PlantID,
		GroupID:        plant.GroupID,
		Name:           plant.Name,
		ScientificName: plant.ScientificName,
		Description:    plant.Description,
		GrowthDays:     plant.GrowthDays,
		Height:         plant.Height,
		LeafColor:      plant.LeafColor,
		Floor:          plant.Floor,
		Humidity:       plant.Humidity,
		Temperature:    plant.Temperature,
		SeedingDate:    plant.SeedingDate,
		RecordedDate:   plant.RecordedDate,
		HarvestDate:    plant.HarvestDate,
		GrowthStage:    plant.GrowthStage,
	}

	_, err = plantCollection.InsertOne(ctx, doc)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to insert plant"})
		return
	}

	c.JSON(http.StatusCreated, doc)
}

// UpdatePlant godoc
// @Summary Update an existing plant
// @Description Update plant information such as seeding date, harvesting date, etc.
// @Tags Admin - Plants
// @Accept json
// @Produce json
// @Param plant_id path int true "Plant ID"
// @Param plant body models.UpdatePlantRequest true "Updated plant data"
// @Success 200 {object} models.SuccessResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 404 {object} models.ErrorResponse
// @Router /plants/{plant_id} [put]
// @Security BearerAuth
func UpdatePlant(c *gin.Context) {
	plantIDParam := c.Param("plant_id")
	plantID, err := strconv.Atoi(plantIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid plant ID"})
		return
	}

	var updatedPlant models.UpdatePlantRequest
	if err := c.ShouldBindJSON(&updatedPlant); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	filter := bson.M{"plant_id": plantID}

	var updateDoc PlantUpdateFields

	if updatedPlant.Name != "" {
		updateDoc.Name = updatedPlant.Name
	}
	if updatedPlant.ScientificName != "" {
		updateDoc.ScientificName = updatedPlant.ScientificName
	}
	if updatedPlant.GrowthDays > 0 {
		updateDoc.GrowthDays = updatedPlant.GrowthDays
		now := time.Now()
		updateDoc.SeedingDate = now
		updateDoc.HarvestDate = now.Add(time.Hour * 24 * time.Duration(updatedPlant.GrowthDays))
	}
	if updatedPlant.Description != "" {
		updateDoc.Description = updatedPlant.Description
	}
	if updatedPlant.Height > 0 {
		updateDoc.Height = updatedPlant.Height
	}
	if updatedPlant.LeafColor != "" {
		updateDoc.LeafColor = updatedPlant.LeafColor
	}
	if updatedPlant.Floor != "" {
		updateDoc.Floor = updatedPlant.Floor
	}
	if updatedPlant.Humidity > 0 {
		updateDoc.Humidity = updatedPlant.Humidity
	}
	if updatedPlant.Temperature > 0 {
		updateDoc.Temperature = updatedPlant.Temperature
	}

	if updatedPlant.GroupID != "" {
		updateDoc.GroupID = updatedPlant.GroupID
	}

	if updatedPlant.GrowthStage != "" {
		updateDoc.GrowthStage = updatedPlant.GrowthStage
	}

	update := bson.M{"$set": updateDoc}

	result, err := plantCollection.UpdateOne(context.Background(), filter, update)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update plant"})
		return
	}
	if result.MatchedCount == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Plant not found"})
		return
	}

	var updated bson.M
	err = plantCollection.FindOne(context.Background(), filter).Decode(&updated)
	if err != nil {
		fmt.Println("❌ Plant disappeared after update!")
	} else {
		fmt.Printf("✅ Document after update: %+v\n", updated)
	}

	c.JSON(http.StatusOK, gin.H{"message": "Plant updated successfully"})
}

// DeletePlant godoc
// @Summary Delete a plant
// @Description Remove a plant entry by its name
// @Tags Admin - Plants
// @Accept json
// @Produce json
// @Param plant_id path int true "Plant ID"
// @Success 200 {object} models.SuccessResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 404 {object} models.ErrorResponse
// @Router /plants/{plant_id} [delete]
// @Security BearerAuth
func DeletePlant(c *gin.Context) {
	plantIDParam := c.Param("plant_id") // Get plant ID from URL parameter

	// Convert plant_id to an integer
	plantID, err := strconv.Atoi(plantIDParam)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid plant ID"})
		return
	}

	// Find and delete the plant
	filter := bson.M{"plant_id": plantID}
	result, err := plantCollection.DeleteOne(context.Background(), filter)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete plant"})
		return
	}

	// Check if a document was deleted
	if result.DeletedCount == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Plant not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Plant deleted successfully"})
}

// DeletePlantsByName godoc
// @Summary Delete all plants by name
// @Description Remove all plant entries that match the given name
// @Tags Admin - Plants
// @Produce json
// @Param name path string true "Plant Name"
// @Success 200 {object} models.SuccessResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /plants/delete-by-name/{name} [delete]
// @Security BearerAuth
func DeletePlantsByName(c *gin.Context) {
	name := c.Param("name")
	fmt.Println("🌿 Received name param:", name) // <- Add this line for debug

	if len(name) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Name is required"})
		return
	}

	filter := bson.M{"name": name}
	result, err := plantCollection.DeleteMany(context.Background(), filter)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete plants"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Deleted %d plant(s) with name '%s'", result.DeletedCount, name),
	})
}

// SearchPlants godoc
// @Summary Search plants
// @Description Search plants based on multiple filters
// @Tags Public - Plants
// @Accept json
// @Produce json
// @Param name query string false "Plant name"
// @Param plant_id query int false "Plant ID" // New query param for plant_id
// @Param group_id query string false "Group ID"
// @Param scientific_name query string false "Scientific name"
// @Param description query string false "Description"
// @Param growth_stage query string false "Growth Stage"
// @Param min_growth_days query int false "Minimum Growth Days"
// @Param max_growth_days query int false "Maximum Growth Days"
// @Param limit query int false "Limit number of results (default 10, max 100)"
// @Param skip query int false "Skip number of results"
// @Param sort_by query string false "Sort field (e.g., name, growth_days)"
// @Param sort_order query string false "Sort order asc or desc"
// @Success 200 {object} models.PlantListResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /plants/search [get]
func SearchPlants(c *gin.Context) {
	collection := config.GetCollection("plants")
	ctx := context.Background()

	filter := bson.M{}
	findOptions := options.Find()

	// Query parameters
	name := c.Query("name")
	scientificName := c.Query("scientific_name")
	description := c.Query("description")
	plantID := c.Query("plant_id") // Get plant_id query parameter
	groupID := c.Query("group_id")
	growthStage := c.Query("growth_stage")

	minGrowthDays := c.Query("min_growth_days")
	maxGrowthDays := c.Query("max_growth_days")

	limitParam := c.DefaultQuery("limit", "10") // default sort by name
	skipParam := c.DefaultQuery("skip", "0")

	sortBy := c.DefaultQuery("sort_by", "name")      // e.g., "growth_days" default sort by name
	sortOrder := c.DefaultQuery("sort_order", "asc") // "asc" or "desc" default ascending

	// Filters
	if name != "" {
		filter["name"] = bson.M{"$regex": name, "$options": "i"}
	}
	if scientificName != "" {
		filter["scientific_name"] = bson.M{"$regex": scientificName, "$options": "i"}
	}
	if description != "" {
		filter["description"] = bson.M{"$regex": description, "$options": "i"}
	}
	if plantID != "" {
		if id, err := strconv.Atoi(plantID); err == nil {
			filter["plant_id"] = id
		} else {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid plant_id"})
			return
		}
	}

	if groupID != "" {
		filter["group_id"] = groupID
	}

	if growthStage != "" {
		filter["growth_stage"] = bson.M{"$regex": growthStage, "$options": "i"}
	}

	// Growth days filter (range)
	if minGrowthDays != "" || maxGrowthDays != "" {
		growthDaysFilter := bson.M{}
		if minGrowthDays != "" {
			min, err := strconv.Atoi(minGrowthDays)
			if err == nil {
				growthDaysFilter["$gte"] = min
			}
		}
		if maxGrowthDays != "" {
			max, err := strconv.Atoi(maxGrowthDays)
			if err == nil {
				growthDaysFilter["$lte"] = max
			}
		}
		filter["growth_days"] = growthDaysFilter
	}

	// Pagination

	limit, err := strconv.ParseInt(limitParam, 10, 64)
	if err != nil || limit <= 0 {
		limit = 10 // default
	}
	if limit > MaxLimit {
		limit = MaxLimit // maximum limit
	}
	findOptions.SetLimit(limit)

	if limitParam != "" {
		limit, err := strconv.ParseInt(limitParam, 10, 64)
		if err == nil {
			findOptions.SetLimit(limit)
		}
	}
	if skipParam != "" {
		skip, err := strconv.ParseInt(skipParam, 10, 64)
		if err == nil {
			findOptions.SetSkip(skip)
		}
	}

	// Sorting
	if sortBy != "" {
		order := 1 // ascending by default
		if sortOrder == "desc" {
			order = -1
		}
		findOptions.SetSort(bson.D{{Key: sortBy, Value: order}})
	}

	// First get total count (without limit/skip)
	total, err := collection.CountDocuments(ctx, filter)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to count plants"})
		return
	}

	// Querying MongoDB
	cursor, err := collection.Find(ctx, filter, findOptions)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to search plants"})
		return
	}
	defer cursor.Close(ctx)

	var plants []models.Plant
	if err = cursor.All(ctx, &plants); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse plants"})
		return
	}

	// Respond
	c.JSON(http.StatusOK, gin.H{
		"total":  total,
		"plants": plants,
	})
}
