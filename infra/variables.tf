variable "subscription_id" {
  type        = string
  description = "Azure subscription id. Get it with: az account show --query id -o tsv"
}

variable "location" {
  type        = string
  default     = "southeastasia"
  description = "Must be a region allowed by your subscription policy (eastasia, uaenorth, malaysiawest, southeastasia, austriaeast)."
}

variable "prefix" {
  type        = string
  default     = "blood"
  description = "Short prefix used in resource names."
}

variable "vm_size" {
  type        = string
  default     = "Standard_B1s"
  description = "VM size. If you get SkuNotAvailable try Standard_B2s or Standard_B1ms."
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
  description = "Path to your SSH PUBLIC key (create it with ssh-keygen -t rsa -b 4096)."
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "Who may SSH into the VM, e.g. 45.112.151.0/24. Do not use 0.0.0.0/0."
}

# ---- switches for parts that student subscriptions sometimes block ----
variable "enable_notification_hub" {
  type    = bool
  default = true
}

variable "enable_function_app" {
  type    = bool
  default = true
}

variable "enable_role_assignments" {
  type    = bool
  default = true
}

# ---- database ----
variable "create_database" {
  type        = bool
  default     = false
  description = "false = reuse the PostgreSQL server you created by hand. true = let Terraform create a new one."
}

variable "existing_db_name" {
  type    = string
  default = "blooddb-isha1000"
}

variable "existing_db_resource_group" {
  type    = string
  default = "rg-blooddonation"
}

variable "db_admin_user" {
  type    = string
  default = "bloodadmin"
}

variable "db_admin_password" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Only needed when create_database = true."
}
