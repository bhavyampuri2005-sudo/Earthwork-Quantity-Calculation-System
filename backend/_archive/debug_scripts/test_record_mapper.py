from ocr.record_mapper import RecordMapper

mapper = RecordMapper()

record = {

    "chainage":80320,

    "ground_level":372.458,

    "formation_level":375.973,

    "rail_level":376.950,

    "cut_fill":3.515,

    "status":"VALID",

    "remarks":""

}

mapped = mapper.map_record(
    record,
    project_id=1
)

print(mapped)