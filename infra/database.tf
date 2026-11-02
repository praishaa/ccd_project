# Default (create_database = false): reuse the PostgreSQL server you created by hand
# and only add a firewall rule so the VM can reach it.
# create_database = true: Terraform builds a brand new server instead.

data "azurerm_postgresql_flexible_server" "existing" {
  count               = var.create_database ? 0 : 1
  name                = var.existing_db_name
  resource_group_name = var.existing_db_resource_group
}

resource "azurerm_postgresql_flexible_server" "db" {
  count                  = var.create_database ? 1 : 0
  name                   = "${var.prefix}db-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.tf.name
  location               = azurerm_resource_group.tf.location
  version                = "16"
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768

  public_network_access_enabled = true
  tags                          = local.tags

  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "blooddb" {
  count     = var.create_database ? 1 : 0
  name      = "blooddb"
  server_id = azurerm_postgresql_flexible_server.db[0].id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

locals {
  db_server_id = var.create_database ? azurerm_postgresql_flexible_server.db[0].id : data.azurerm_postgresql_flexible_server.existing[0].id
  db_host      = var.create_database ? azurerm_postgresql_flexible_server.db[0].fqdn : data.azurerm_postgresql_flexible_server.existing[0].fqdn
}

# Let the application VM connect to the database
resource "azurerm_postgresql_flexible_server_firewall_rule" "vm" {
  name             = "allow-app-vm"
  server_id        = local.db_server_id
  start_ip_address = azurerm_public_ip.vm.ip_address
  end_ip_address   = azurerm_public_ip.vm.ip_address
}
