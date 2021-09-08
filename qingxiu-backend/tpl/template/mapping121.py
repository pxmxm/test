def get_data(progress_report):
    data = {
        'p1': progress_report.name,  # 项目名称
        'p2': progress_report.contractNo,  # 合同编号
        'p3': progress_report.unit,
        'p4': progress_report.head,
        'p5': progress_report.startStopYear,
        'p6': str(progress_report.fillTime),
        'p7': progress_report.workProgress,
        'p8': progress_report.problem,
        'p9': progress_report.planMeasures
    }
    return data
