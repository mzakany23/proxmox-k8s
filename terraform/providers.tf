terraform {
  required_version = ">= 1.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.50"
    }
  }

  backend "s3" {
    bucket = "ncsh-terraform-state"
    key    = "proxmox/terraform.tfstate"
    region = "us-east-2"
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true # Set to false if using valid SSL certificates

  ssh {
    agent    = true
    username = "root"
  }
}
