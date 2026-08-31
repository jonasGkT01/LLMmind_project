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

def model_label(model, stimuli_type):
    return f"{model}-{stimuli_type}"