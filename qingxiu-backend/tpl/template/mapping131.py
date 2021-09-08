

def get_data(field_research):
    data = {

        'p1': str(field_research.times),
        'p2': field_research.place,
        'p3': field_research.personnel,
        'p4': field_research.opinion,
        'p5': field_research.planCategory,
        'p6': field_research.unitName,
        'p7': field_research.subjectName,
    }
    return data
