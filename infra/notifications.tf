# Azure Notification Hubs (free tier)

resource "azurerm_notification_hub_namespace" "ns" {
  count               = var.enable_notification_hub ? 1 : 0
  name                = "${var.prefix}-nhns-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
  namespace_type      = "NotificationHub"
  sku_name            = "Free"
  tags                = local.tags
}

resource "azurerm_notification_hub" "hub" {
  count               = var.enable_notification_hub ? 1 : 0
  name                = "${var.prefix}-hub"
  namespace_name      = azurerm_notification_hub_namespace.ns[0].name
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
  tags                = local.tags
}
