async def validator_node(state: PlannerState) -> PlannerState:
    form_data = state.get("llm_output")

    missing_required = [
        field for field in form_data.get("questions", [])
        if field.get("required") and not field.get("value")
    ]

    if missing_required:
        return {
            **state,
            "follow_up_required": True
        }

    return {
        **state,
        "follow_up_required": False
    }
