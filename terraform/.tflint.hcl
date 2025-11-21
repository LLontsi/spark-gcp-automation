config {
  call_module_type = "all"
  force            = false
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

rule "terraform_unused_declarations" {
  enabled = false
}