variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
}

variable "proxmox_api_token_id" {
  description = "Proxmox API Token ID"
  type        = string
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API Token Secret"
  type        = string
  sensitive   = true
}

variable "proxmox_node" {
  description = "Proxmox node name"
  type        = string
  default     = "pve"
}

variable "template_id" {
  description = "VM template ID to clone"
  type        = number
  default     = 9000
}

variable "ssh_public_key_file" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "vm_user" {
  description = "Default user for VMs"
  type        = string
  default     = "ubuntu"
}

variable "control_plane_config" {
  description = "Control plane node configuration"
  type = object({
    name   = string
    cores  = number
    memory = number
    disk   = number
    ip     = string
  })
}

variable "worker_nodes" {
  description = "Worker node configurations"
  type = list(object({
    name   = string
    cores  = number
    memory = number
    disk   = number
    ip     = string
  }))
}

variable "milvus_node_config" {
  description = "Milvus dedicated node configuration"
  type = object({
    name   = string
    cores  = number
    memory = number
    disk   = number
    ip     = string
  })
}

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "network_gateway" {
  description = "Network gateway"
  type        = string
  default     = "192.168.68.1"
}

variable "dns_servers" {
  description = "DNS servers"
  type        = list(string)
  default     = ["192.168.68.1", "8.8.8.8"]
}

variable "k3s_version" {
  description = "k3s version channel"
  type        = string
  default     = "stable"
}
