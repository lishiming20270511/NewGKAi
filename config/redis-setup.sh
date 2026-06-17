#!/bin/bash
# Redis configuration for production (T1.1)
# Run once after installing Redis: bash config/redis-setup.sh

set -e

echo "Configuring Redis for production..."

redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 536870912    # 512MB
redis-cli CONFIG SET save "3600 1"
redis-cli CONFIG REWRITE

echo "Verifying Redis config:"
redis-cli CONFIG GET maxmemory-policy
redis-cli CONFIG GET save
redis-cli CONFIG GET maxmemory

echo "Redis config done."
