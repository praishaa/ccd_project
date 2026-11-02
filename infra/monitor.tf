# Azure Monitor: Log Analytics workspace + Application Insights

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${var.prefix}-logs"
  location            = azurerm_resource_group.tf.location
  resource_group_name = azurerm_resource_group.tf.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "appi" {
  name                = "${var.prefix}-appinsights"
  location            = azurerm_resource_group.tf.location
  resource_group_name = azurerm_resource_group.tf.name
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "web"
  tags                = local.tags
}
output "appinsights_connection_string" {
  value     = azurerm_application_insights.appi.connection_string
  sensitive = true
}
variable "alert_email" {
  type = string
}

resource "azurerm_monitor_action_group" "email" {
  name                = "${var.prefix}-alerts"
  resource_group_name = azurerm_resource_group.tf.name
  short_name          = "alerts"
  tags                = local.tags

  email_receiver {
    name          = "me"
    email_address = var.alert_email
  }
}
resource "azurerm_notification_hub_namespace" "nh" {
  name                = "${var.prefix}-nhns"
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
  namespace_type      = "NotificationHub"
  sku_name            = "Free"
  tags                = local.tags
}

resource "azurerm_notification_hub" "nh" {
  name                = "${var.prefix}-hub"
  namespace_name      = azurerm_notification_hub_namespace.nh.name
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
}
