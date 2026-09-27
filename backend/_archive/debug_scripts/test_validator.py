from ocr.validator import Validator

validator = Validator()

records = [

    {
        "chainage":80320,
        "ground_level":372.458,
        "formation_level":375.973,
        "rail_level":376.950,
        "cut_fill":3.515
    },

    {
        "chainage":80340,
        "ground_level":372.462,
        "formation_level":375.980,
        "rail_level":376.960,
        "cut_fill":3.518
    }

]

validated = validator.validate(records)

for row in validated:
    print(row)