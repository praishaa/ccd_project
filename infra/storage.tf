resource "azurerm_storage_account" "store" {
  name                     = "blooddon${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.tf.name
  location                 = azurerm_resource_group.tf.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

# analytics / report exports written by the backend
resource "azurerm_storage_container" "exports" {
  name                  = "exports"
  storage_account_id    = azurerm_storage_account.store.id
  container_access_type = "private"
}

# datasets and ML files
resource "azurerm_storage_container" "ml_data" {
  name                  = "ml-data"
  storage_account_id    = azurerm_storage_account.store.id
  container_access_type = "private"
}
