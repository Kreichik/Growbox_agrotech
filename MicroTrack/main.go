package main

import (
	"MicroTrack/config"
	"MicroTrack/controllers"
	_ "MicroTrack/docs"
	"MicroTrack/routes"
	"github.com/gin-gonic/gin"
)

// @securityDefinitions.apikey BearerAuth
// @in header
// @name Authorization

// @title MicroTrack API
// @version 1.0
// @description This is the backend for MicroTrack application.
// @termsOfService http://swagger.io/terms/

// @contact.name Hamed Frogh
// @contact.email your-email@example.com

// @license.name MIT
// @license.url https://opensource.org/licenses/MIT

// @host localhost:8080
// @BasePath /

func main() {
	config.ConnectDB()
	controllers.InitPlantController() // Call this AFTER connecting to DB
	router := gin.Default()
	routes.Routes(router)

	router.Run(":8080")
}
