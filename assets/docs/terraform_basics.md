# Terraform Basics

Terraform is an infrastructure-as-code tool used to provision and manage cloud resources. Configuration is written in
HashiCorp Configuration Language (HCL) and executed via the Terraform CLI.

## Workflow overview

A typical Terraform workflow is:

1. **Write configuration** in `.tf` files describing resources such as virtual machines, databases, and networks.
2. Run `terraform init` to download providers and initialize the working directory.
3. Run `terraform plan` to preview the changes Terraform will make.
4. Run `terraform apply` to execute the plan and create or modify resources.
5. Run `terraform destroy` to tear down resources when they are no longer needed.

Terraform keeps track of the state of your infrastructure in a **state file**. The state file is critical, because it
maps Terraform resources in your configuration to real resources in the cloud.

## State management

For local experiments, the state file is stored as `terraform.tfstate` in the working directory. For teams, the state
file should be stored remotely, for example in an S3 bucket or a Terraform Cloud workspace.

Remote state enables:

- Team collaboration
- State locking to avoid concurrent applies
- Backups and versioning of the state file

Losing the state file does not destroy the resources, but Terraform can no longer safely manage them.

## Modules and composition

A **module** is a reusable unit of Terraform configuration. The root module is the directory where you run Terraform
commands. Child modules can be called using the `module` block.

Modules help you:

- Encapsulate patterns such as “VPC + subnets + routing”
- Enforce standards (tags, naming conventions)
- Reduce duplication across environments

## Best practices

Some common Terraform best practices are:

- Keep environments separate (for example, `envs/dev`, `envs/staging`, `envs/prod`)
- Use remote state with locking for shared environments
- Store state in a secure location with restricted access
- Use variables and outputs to parameterize modules
- Run `terraform fmt` and `terraform validate` in CI

## When to use Terraform

Terraform is useful when:

- You manage multiple cloud resources that should be reproducible
- You want reviewable, version-controlled infrastructure changes
- You need to coordinate resources across different providers or accounts