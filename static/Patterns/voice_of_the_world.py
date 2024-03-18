# Voice of the World Regular Expressions

## Patterns

### Killed

patterns = {
    "punctuation": [
        r"(“)", r"(”)", r"(〝)", r"(〞)"
    ],
    "killed": [
        r"(\"?.*ordinary.+killed.+beast soul.+\"?)",
        r"(\"?.*primitive.+killed.+beast soul.+\"?)",
        r"(\"?.*mutant.+killed.+beast soul.+\"?)",
        r"(\"?.*sacred[- ]?blood.+killed.+beast soul.+\"?)",
        r"(\"?.*super.+killed.+beast soul.+\"?)"
    ],
    "hunted": [
        r"(\"?.*ordinary.+hunted\..+beast soul.+\"?)",
        r"(\"?.*primitive.+hunted\..+beast soul.+\"?)",
        r"(\"?.*mutant.+hunted.+beast soul.+\"?)",
        r"(\"?.*sacred[- ]?blood.+hunted.+beast soul.+\"?)",
        r"(\"?.*super.+hunted.+beast soul.+\"?)"
    ],
    "eaten": [
        r"(\"?.*ordinary.+eaten.+geno point.+\"?)",
        r"(\"?.*primitive.+eaten.+geno point.+\"?)",
        r"(\"?.*mutant.+eaten.+geno point.+\"?)",
        r"(\"?.*sacred[- ]?blood.+eaten.+geno point.+\"?)",
        r"(\"?.*life essence.+eaten.+geno point.+\"?)",
        r"(\"?.*meat.+eaten.+geno point.+\"?)",
        r"(\"?.*flesh.+eaten.+geno point.+\"?)",
    ],
    "consumed": [
        r"(\"?.*ordinary.+consumed.+geno point.+\"?)",
        r"(\"?.*primitive.+consumed.+geno point.+\"?)",
        r"(\"?.*mutant.+consumed.+geno point.+\"?)",
        r"(\"?.*sacred[- ]?blood.+consumed.+geno point.+\"?)",
        r"(\"?.*life essence.+consumed.+geno point.+\"?)",
        r"(\"?.*meat.+consumed.+geno point.+\"?)",
    ]
}
# (?P<super_consumed>\"?.*life essence.+consumed.+geno point.+\")|(?P<flesh_eaten>^\".*flesh.+eatan.+\"$)|(?P<killed_gainmax>\".*killed.+gain.+geno point.+\")|(?P<young_gained>\".*young.+geno point.+\")
