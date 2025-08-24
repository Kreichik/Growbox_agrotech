package controllers

import (
	"context"
	"github.com/golang-jwt/jwt/v5"
	"net/http"
	"time"

	"MicroTrack/config"
	"MicroTrack/models"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"golang.org/x/crypto/bcrypt"
)

// Secret Key for JWT
var jwtSecret = []byte("your_secret_key")

// Signup godoc
// @Summary Register a new user
// @Description Create a new user account (default role is \"user\" unless specified).
// @Tags Public - Auth
// @Accept json
// @Produce json
// @Param user body models.User true "User signup data"
// @Success 201 {object} models.SuccessResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /signup [post]
func Signup(c *gin.Context) {
	var user models.User
	if err := c.ShouldBindJSON(&user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if user.FirstName == "" || user.LastName == "" || user.Username == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "First name and last name, and username are required"})
		return
	}

	// Check if email already exists
	emailFilter := bson.M{"email": user.Email}
	emailExists := config.GetCollection("users").FindOne(context.Background(), emailFilter)
	if emailExists.Err() == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Email already registered"})
		return
	}
	if emailExists.Err() != nil && emailExists.Err().Error() != "mongo: no documents in result" {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error while checking email"})
		return
	}

	// Check if username already exists
	usernameFilter := bson.M{"username": user.Username}
	usernameExists := config.GetCollection("users").FindOne(context.Background(), usernameFilter)
	if usernameExists.Err() == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Username already taken"})
		return
	}
	if usernameExists.Err() != nil && usernameExists.Err().Error() != "mongo: no documents in result" {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error while checking username"})
		return
	}

	// Hash the password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
		return
	}
	user.Password = string(hashedPassword)

	// Force role to "user"
	user.Role = "user"

	// Insert into MongoDB
	user.ID = primitive.NewObjectID()
	_, err = config.GetCollection("users").InsertOne(context.Background(), user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "User registered successfully"})
}

// Login godoc
// @Summary Login a user
// @Description Authenticate a user and return a JWT token if credentials are valid.
// @Tags Public - Auth
// @Accept json
// @Produce json
// @Param credentials body models.User true "User login credentials"
// @Success 200 {object} models.LoginResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 401 {object} models.ErrorResponse
// @Failure 500 {object} models.ErrorResponse
// @Router /login [post]
func Login(c *gin.Context) {
	var credentials models.User
	if err := c.ShouldBindJSON(&credentials); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	var user models.User
	filter := bson.M{"$or": []bson.M{
		{"email": credentials.Email},
		{"username": credentials.Username},
	}}
	err := config.GetCollection("users").FindOne(context.Background(), filter).Decode(&user)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid username/email or password"})
		return
	}

	// Compare hashed password
	err = bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(credentials.Password))
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
		return
	}

	// Generate JWT token
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"userID": user.ID.Hex(),
		"role":   user.Role,
		"exp":    time.Now().Add(time.Hour * 24).Unix(),
	})

	tokenString, err := token.SignedString(jwtSecret)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"token": tokenString, "role": user.Role, "first_name": user.FirstName,
		"last_name": user.LastName, "username": user.Username})
}

// PromoteUserToAdmin godoc
// @Summary Promote a user to admin
// @Description Only an existing admin can promote other users
// @Tags Admin - Auth
// @Accept json
// @Produce json
// @Param username path string true "Username to promote"
// @Success 200 {object} models.SuccessResponse
// @Failure 400 {object} models.ErrorResponse
// @Failure 401 {object} models.ErrorResponse
// @Failure 403 {object} models.ErrorResponse
// @Failure 404 {object} models.ErrorResponse
// @Router /admin/promote/{username} [patch]
// @Security BearerAuth
func PromoteUserToAdmin(c *gin.Context) {
	username := c.Param("username")
	if username == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Username is required"})
		return
	}

	// Check if user exists
	filter := bson.M{"username": username}
	update := bson.M{"$set": bson.M{"role": "admin"}}

	result, err := config.GetCollection("users").UpdateOne(context.Background(), filter, update)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to promote user"})
		return
	}

	if result.MatchedCount == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "User promoted to admin successfully"})
}
