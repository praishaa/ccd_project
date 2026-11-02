locals {
  tags = {
    project    = "blood-donation"
    managed_by = "terraform"
  }
}

# Used to make globally-unique names (storage account, function app, ...)
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "tf" {
  name     = "rg-blooddonation-tf"
  location = var.location
  tags     = local.tags
}
