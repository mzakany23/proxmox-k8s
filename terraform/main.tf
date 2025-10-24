# Read SSH public key
locals {
  ssh_public_key = file(pathexpand(var.ssh_public_key_file))
}

# Generate k3s token for cluster
resource "random_password" "k3s_token" {
  length  = 32
  special = false
}

# Control Plane Node
resource "proxmox_virtual_environment_vm" "control_plane" {
  name        = var.control_plane_config.name
  description = "Kubernetes Control Plane Node"
  node_name   = var.proxmox_node

  clone {
    vm_id = var.template_id
    full  = true
  }

  cpu {
    cores = var.control_plane_config.cores
    type  = "host"
  }

  memory {
    dedicated = var.control_plane_config.memory
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = var.control_plane_config.disk
  }

  network_device {
    bridge = var.network_bridge
  }

  operating_system {
    type = "l26"
  }

  agent {
    enabled = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.control_plane_config.ip}/24"
        gateway = var.network_gateway
      }
    }

    dns {
      servers = var.dns_servers
    }

    user_account {
      username = var.vm_user
      keys     = [local.ssh_public_key]
    }

    user_data_file_id = proxmox_virtual_environment_file.control_plane_cloud_init.id
  }

  lifecycle {
    ignore_changes = [
      network_device,
    ]
  }
}

# Worker Nodes
resource "proxmox_virtual_environment_vm" "workers" {
  count       = length(var.worker_nodes)
  name        = var.worker_nodes[count.index].name
  description = "Kubernetes Worker Node ${count.index + 1}"
  node_name   = var.proxmox_node

  clone {
    vm_id = var.template_id
    full  = true
  }

  cpu {
    cores = var.worker_nodes[count.index].cores
    type  = "host"
  }

  memory {
    dedicated = var.worker_nodes[count.index].memory
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = var.worker_nodes[count.index].disk
  }

  network_device {
    bridge = var.network_bridge
  }

  operating_system {
    type = "l26"
  }

  agent {
    enabled = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.worker_nodes[count.index].ip}/24"
        gateway = var.network_gateway
      }
    }

    dns {
      servers = var.dns_servers
    }

    user_account {
      username = var.vm_user
      keys     = [local.ssh_public_key]
    }

    user_data_file_id = proxmox_virtual_environment_file.worker_cloud_init[count.index].id
  }

  depends_on = [proxmox_virtual_environment_vm.control_plane]

  lifecycle {
    ignore_changes = [
      network_device,
    ]
  }
}

# Milvus Dedicated Node
resource "proxmox_virtual_environment_vm" "milvus_node" {
  name        = var.milvus_node_config.name
  description = "Kubernetes Milvus Dedicated Node"
  node_name   = var.proxmox_node

  clone {
    vm_id = var.template_id
    full  = true
  }

  cpu {
    cores = var.milvus_node_config.cores
    type  = "host"
  }

  memory {
    dedicated = var.milvus_node_config.memory
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = var.milvus_node_config.disk
  }

  network_device {
    bridge = var.network_bridge
  }

  operating_system {
    type = "l26"
  }

  agent {
    enabled = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.milvus_node_config.ip}/24"
        gateway = var.network_gateway
      }
    }

    dns {
      servers = var.dns_servers
    }

    user_account {
      username = var.vm_user
      keys     = [local.ssh_public_key]
    }

    user_data_file_id = proxmox_virtual_environment_file.milvus_cloud_init.id
  }

  depends_on = [proxmox_virtual_environment_vm.control_plane]

  lifecycle {
    ignore_changes = [
      network_device,
    ]
  }
}

# Cloud-init configuration for control plane
resource "proxmox_virtual_environment_file" "control_plane_cloud_init" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = var.proxmox_node

  source_raw {
    data = templatefile("${path.module}/cloud-init/control-plane.yaml.tpl", {
      hostname   = var.control_plane_config.name
      k3s_token  = random_password.k3s_token.result
      k3s_version = var.k3s_version
    })
    file_name = "control-plane-cloud-init.yaml"
  }
}

# Cloud-init configuration for workers
resource "proxmox_virtual_environment_file" "worker_cloud_init" {
  count        = length(var.worker_nodes)
  content_type = "snippets"
  datastore_id = "local"
  node_name    = var.proxmox_node

  source_raw {
    data = templatefile("${path.module}/cloud-init/worker.yaml.tpl", {
      hostname        = var.worker_nodes[count.index].name
      k3s_token       = random_password.k3s_token.result
      k3s_version     = var.k3s_version
      control_plane_ip = proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0]
    })
    file_name = "worker-${count.index}-cloud-init.yaml"
  }

  depends_on = [proxmox_virtual_environment_vm.control_plane]
}

# Cloud-init configuration for Milvus node
resource "proxmox_virtual_environment_file" "milvus_cloud_init" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = var.proxmox_node

  source_raw {
    data = templatefile("${path.module}/cloud-init/milvus-worker.yaml.tpl", {
      hostname        = var.milvus_node_config.name
      k3s_token       = random_password.k3s_token.result
      k3s_version     = var.k3s_version
      control_plane_ip = proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0]
    })
    file_name = "milvus-cloud-init.yaml"
  }

  depends_on = [proxmox_virtual_environment_vm.control_plane]
}
