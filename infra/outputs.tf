output "resource_group" {
  value = azurerm_resource_group.tf.name
}

output "vm_public_ip" {
  value = azurerm_public_ip.vm.ip_address
}

output "ssh_command" {
  value = "ssh ${var.admin_username}@${azurerm_public_ip.vm.ip_address}"
}

output "api_url" {
  value = "http://${azurerm_public_ip.vm.ip_address}:8000"
}

output "storage_account_name" {
  value = azurerm_storage_account.store.name
}

output "database_host" {
  value = local.db_host
}

output "app_insights_connection_string" {
  value     = azurerm_application_insights.appi.connection_string
  sensitive = true
}

output "function_app_name" {
  value = var.enable_function_app ? azurerm_linux_function_app.func[0].name : null
}

output "notification_hub_name" {
  value = var.enable_notification_hub ? azurerm_notification_hub.hub[0].name : null
}
