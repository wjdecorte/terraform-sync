# terraform-sync

## tfsync

GOAL: CLI tool to sync Terraform configuration files, state file and objects deployed in current environment.

Current State:
As of the initial release, it only attempts a dumb sync by querying for specific objects in the current environment
and attempts to import the object into the state file.  Failures are tolerated since the object may already exist in 
the state file.

