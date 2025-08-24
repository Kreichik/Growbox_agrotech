package config

import (
	"context"
	"fmt"
	"github.com/joho/godotenv"
	"log"
	"os"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var DB *mongo.Database
var client *mongo.Client

func ConnectDB() {
	// Load the appropriate .env file based on the APP_ENV variable
	env := os.Getenv("APP_ENV")
	var err error

	if env == "production" {
		// Load production .env file
		err = godotenv.Load(".env.production")
	} else {
		// Load the default .env file
		err = godotenv.Load(".env")
	}

	if err != nil {
		log.Fatalf("❌ Error loading .env file: %v", err)
	}

	// Get MongoDB URI from the environment variable
	mongoURI := os.Getenv("MONGO_URI")
	if mongoURI == "" {
		log.Fatal("❌ MONGO_URI not set in environment variables")
	}

	fmt.Println("🛠️ Connecting to MongoDB...") // Debugging log

	// Define MongoDB connection options
	clientOptions := options.Client().ApplyURI(mongoURI)

	// Set up a timeout for the connection, with the ability to configure it via .env file
	timeout := os.Getenv("MONGO_TIMEOUT")
	duration, err := time.ParseDuration(timeout + "s")
	if err != nil {
		log.Fatal("❌ Invalid timeout value:", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), duration)
	defer cancel()

	// Connect to MongoDB
	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		log.Fatal("❌ Failed to connect to MongoDB:", err)
	}

	// Ping the database to verify connection
	err = client.Ping(ctx, nil)
	if err != nil {
		log.Fatal("❌ MongoDB ping failed:", err)
	}

	// Assign the database instance to the global variable
	DB = client.Database("microtrack")

	fmt.Println("✅ Connected to MongoDB!") // Debugging log

}

func GetCollection(collectionName string) *mongo.Collection {
	if DB == nil {
		log.Fatal("❌ Database connection not initialized. Call ConnectDB() first.") // Debugging log
	}
	fmt.Println("📂 Fetching collection:", collectionName) // Debugging log
	return DB.Collection(collectionName)
}
