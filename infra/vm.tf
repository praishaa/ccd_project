resource "azurerm_linux_virtual_machine" "app" {
  name                = "${var.prefix}-vm"
  resource_group_name = azurerm_resource_group.tf.name
  location            = azurerm_resource_group.tf.location
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids           = [azurerm_network_interface.vm.id]
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-arm64"
    version   = "latest"
  }

  # Managed identity: lets the VM call Blob Storage without passwords (Entra ID / RBAC)
  identity {
    type = "SystemAssigned"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
    admin_username = var.admin_username
  }))

  tags = local.tags
  lifecycle {
    ignore_changes = [admin_ssh_key]
  }
}
