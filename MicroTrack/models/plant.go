package models

import "time"

type Plant struct {
	ID             string    `json:"id,omitempty" bson:"_id,omitempty"`
	PlantID        int       `json:"plant_id,omitempty" bson:"plant_id,omitempty"`
	GroupID        string    `json:"group_id,omitempty" bson:"group_id,omitempty"`
	Name           string    `json:"name" bson:"name"`
	ScientificName string    `json:"scientific_name" bson:"scientific_name"`
	RecordedDate   time.Time `json:"recorded_date" bson:"recorded_date"`
	SeedingDate    time.Time `json:"seeding_date" bson:"seeding_date"`
	HarvestDate    time.Time `json:"harvest_date" bson:"harvest_date"`
	GrowthDays     int       `json:"growth_days" bson:"growth_days"`
	Description    string    `json:"description" bson:"description"`
	Height         float64   `json:"height" bson:"height"`
	LeafColor      string    `json:"leaf_color" bson:"leaf_color"`
	Floor          string    `json:"floor" bson:"floor"`
	Humidity       float64   `json:"humidity" bson:"humidity"`
	Temperature    float64   `json:"temperature" bson:"temperature"`
	GrowthStage    string    `json:"growth_stage" bson:"growth_stage"`
	TestData 	   string    `json:"test_data" bson:"test_data"`
}

type PlantListResponse struct {
	Total  int     `json:"total" example:"100"`
	Plants []Plant `json:"plants"`
}

type UpdatePlantRequest struct {
	Name           string    `json:"name" bson:"name"`
	GroupID        string    `json:"group_id,omitempty" bson:"group_id,omitempty"`
	ScientificName string    `json:"scientific_name" bson:"scientific_name"`
	SeedingDate    time.Time `json:"seeding_date" bson:"seeding_date"`
	HarvestDate    time.Time `json:"harvest_date" bson:"harvest_date"`
	GrowthDays     int       `json:"growth_days" bson:"growth_days"`
	Description    string    `json:"description" bson:"description"`
	Height         float64   `json:"height" bson:"height"`
	LeafColor      string    `json:"leaf_color" bson:"leaf_color"`
	Floor          string    `json:"floor" bson:"floor"`
	Humidity       float64   `json:"humidity" bson:"humidity"`
	Temperature    float64   `json:"temperature" bson:"temperature"`
	GrowthStage    string    `json:"growth_stage" bson:"growth_stage"`
}

type LoginResponse struct {
	Token string `json:"token" example:"your_jwt_token_here"`
	Role  string `json:"role" example:"admin"`
}

type SuccessResponse struct {
	Message string `json:"message" example:"Plant updated successfully"`
}

type ErrorResponse struct {
	Error string `json:"error" example:"Invalid plant data provided"`
}
