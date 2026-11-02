# Microsoft Entra ID / Azure RBAC: least-privilege access between cloud resources.
# The VM's managed identity may read/write blobs in our storage account, nothing else.

resource "azurerm_role_assignment" "vm_blob" {
  count                = var.enable_role_assignments ? 1 : 0
  scope                = azurerm_storage_account.store.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_virtual_machine.app.identity[0].principal_id
}

resource "azurerm_role_assignment" "func_blob" {
  count                = (var.enable_role_assignments && var.enable_function_app) ? 1 : 0
  scope                = azurerm_storage_account.store.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_linux_function_app.func[0].identity[0].principal_id
}
