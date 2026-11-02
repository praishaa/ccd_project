# Azure Functions (consumption plan). The timer function code that calls
# POST /inventory/check-alerts is deployed later; this creates the app itself.

resource "azurerm_service_plan" "func" {
  count               = var.enable_function_app ? 1 : 0
  name                = "${var.prefix}-func-plan"
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
  os_type             = "Linux"
  sku_name            = "Y1"
  tags                = local.tags
}

resource "azurerm_linux_function_app" "func" {
  count               = var.enable_function_app ? 1 : 0
  name                = "${var.prefix}-func-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location

  service_plan_id            = azurerm_service_plan.func[0].id
  storage_account_name       = azurerm_storage_account.store.name
  storage_account_access_key = azurerm_storage_account.store.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    API_BASE_URL                          = "http://${azurerm_public_ip.vm.ip_address}:8000"
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.appi.connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}
