package routes

import (
	"MicroTrack/controllers"
	"MicroTrack/middlewares"
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

func Routes(router *gin.Engine) {

	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	router.POST("/signup", controllers.Signup)

	router.POST("/login", controllers.Login)

	// Plant routes
	plantRoutes := router.Group("/plants")
	{

		plantRoutes.GET("/", controllers.GetPlants) // Public access (Authenticated users)

		plantRoutes.GET("/search", controllers.SearchPlants)

		// Admin-protected routes
		plantRoutes.Use(middlewares.AuthMiddleware()) // Require authentication
		adminRoutes := plantRoutes.Group("/")
		adminRoutes.Use(middlewares.AdminMiddleware()) // Require admin role
		{

			adminRoutes.POST("/", controllers.AddPlant)

			adminRoutes.PUT("/:plant_id", controllers.UpdatePlant)

			adminRoutes.DELETE("/:plant_id", controllers.DeletePlant)

			adminRoutes.DELETE("/delete-by-name/:name", controllers.DeletePlantsByName)
		}

		// Admin user management
		adminUserRoutes := router.Group("/admin")
		adminUserRoutes.Use(middlewares.AuthMiddleware(), middlewares.AdminMiddleware())
		adminUserRoutes.PATCH("/promote/:username", controllers.PromoteUserToAdmin)

	}

}
