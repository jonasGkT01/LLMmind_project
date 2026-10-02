# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

def parse_model_parameters(model_parameters):
    parameters_by_model = {}

    for model_parameter in model_parameters:
        if "=" not in model_parameter:
            raise ValueError(
                f"Invalid model-parameter specification: {model_parameter}"
            )

        model, number_of_parameters = (model_parameter.split("=", 1))

        if model in parameters_by_model:
            raise ValueError(
                f"Parameters were provided more than once for model {model}"
            )

        parameters_by_model[model] = float(number_of_parameters)

    return parameters_by_model

def model_family(model):
    if "_" not in model:
        return model

    return model.rsplit("_", 1)[0]

def model_key(model, stimuli_type):
    return f"{model}-{stimuli_type}"

def model_sort_key(model, stimuli_type, parameters_by_model):
    # family (alphabetical) -> number of parameters -> model -> stimulus type
    if model not in parameters_by_model:
        raise ValueError(f"No number of parameters was provided for model {model}")

    return (model_family(model), parameters_by_model[model], model, stimuli_type,)

def sort_models(df, parameters_by_model):
    # the rows of a dataframe with model and stimuli_type columns, in model_sort_key order
    sort_keys = [
        model_sort_key(row.model, row.stimuli_type, parameters_by_model)
        for row in df.itertuples(index = False)
    ]
    order = sorted(range(len(df)), key = sort_keys.__getitem__)

    return df.iloc[order].reset_index(drop = True)

def sorted_pairwise_labels(model_metadata, parameters_by_model):
    # the model labels of a pairwise heatmap in model_sort_key order, followed by the brain
    model_labels = sorted(
        model_metadata, 
        key = lambda label: model_sort_key(
            model_metadata[label]["model"], 
            model_metadata[label]["stimuli_type"], 
            parameters_by_model, 
        ), 
    )

    return model_labels + ["brain"]
