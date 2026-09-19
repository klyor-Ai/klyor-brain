# Klyor Brain

Klyor Brain is the AI research and training laboratory behind Klyor AI.

The goal is to develop a specialized coding and creation model capable of:

- understanding natural-language build requests
- generating complete websites
- generating games
- editing existing projects
- understanding project files
- debugging code
- fixing build errors
- reasoning about UI/UX
- using development tools
- validating generated projects
- recovering from failed builds
- maintaining project context

## Architecture

Base model
→ Klyor datasets
→ training
→ evaluation
→ agent/tool system
→ Klyor Brain runtime
→ Klyor AI provider

## Initial base model

Qwen3-Coder family.

The model itself is not trained from scratch.

Klyor Brain specializes an existing open-weight coding model using
Klyor-specific data, training and evaluation.

## Repository

datasets/
training/
evaluation/
benchmarks/
models/
experiments/
prompts/
agent/
runtime/
scripts/
configs/
docs/

## Long-term goal

Klyor Brain should eventually be usable by Klyor AI as:

Klyor Brain
Klyor Brain Fast
Klyor Brain Coder

through the same provider abstraction used by external AI providers.
