package models

import "go.mongodb.org/mongo-driver/bson/primitive"

type User struct {
	ID        primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	Username  string             `json:"username" bson:"username"`
	FirstName string             `json:"first_name" bson:"first_name"`
	LastName  string             `json:"last_name" bson:"last_name"`
	Email     string             `bson:"email" json:"email"`
	Password  string             `bson:"password,omitempty"`
	Role      string             `bson:"role" json:"role"` // "admin" or "user"
}
