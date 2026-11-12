terraform {
  backend "gcs" {
    bucket = "adk-chatbot-prod-terraform-state"
    prefix = "adk-chatbot/prod"
  }
}
