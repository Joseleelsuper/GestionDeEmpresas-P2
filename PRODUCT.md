# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: FastAPI with static HTML, CSS, and JavaScript, chosen for a small local application.

## Users

Students working on the production programming exercise in Gestión y Organización de Empresas.

## Product Purpose

Load a flow shop permutation instance, choose or generate an order sequence, calculate its completion-time matrix and performance measures, and optionally improve the sequence with local search.

## Operating Context

Course material supplies TXT instances; students may also upload a compatible TXT file.

## Capabilities and Constraints

Use permutation flow shop data with all jobs released at time zero. Show the completion matrix F, Cmax, Fmax. Local search minimizes the selected measure with a bounded iteration count and stops when no improving neighbor remains or the limit is reached; it does not guarantee a global optimum. User uploads are temporary. Do not draw a Gantt chart.

## Evidence on Hand

The repository contains the course PDFs, a ZIP of 13 TXT examples, and a flow shop exercise diagram.

## Product Principles

- Keep the tool small and quick to run locally.
- Explain the completion-time recurrence in the Python docstrings.
- Make input and resulting values easy to inspect.
