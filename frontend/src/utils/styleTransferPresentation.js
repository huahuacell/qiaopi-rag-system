const severity = {
  pending: 0,
  pass: 1,
  warn: 2,
  fail: 3
}

export function normalizeStyleTransferCheck(result, hasGeneratedText = false) {
  const direct = result?.consistency_check
  if (direct) {
    return {
      status: direct.status || 'pending',
      checks: direct.checks || [],
      warnings: direct.warnings || [],
      passed_rules: direct.passed_rules || [],
      failed_rules: direct.failed_rules || []
    }
  }

  const report = result?.validation_report
  if (!report) {
    return {
      status: hasGeneratedText ? 'passed' : 'pending',
      checks: [],
      warnings: [],
      passed_rules: [],
      failed_rules: []
    }
  }

  return {
    status: report.is_consistent ? 'passed' : 'failed',
    risk_level: report.risk_level || 'low',
    summary: report.summary || '',
    checks: report.checks || [],
    warnings: [
      ...(report.possible_hallucinations || []),
      ...(report.missing_required_facts || []),
      ...(report.unsupported_new_facts || [])
    ],
    passed_rules: (report.checks || [])
      .filter((item) => item.status === 'pass')
      .map((item) => item.message),
    failed_rules: (report.checks || [])
      .filter((item) => item.status === 'fail')
      .map((item) => item.message)
  }
}

function cardFromChecks(checks, names, label, fallback) {
  const related = checks.filter((item) => names.includes(item.name))
  if (!related.length) {
    return {
      label,
      status: 'pass',
      ok: true,
      detail: fallback
    }
  }

  const worst = [...related].sort((left, right) => {
    const severityDifference = severity[right.status] - severity[left.status]
    if (severityDifference) return severityDifference
    return names.indexOf(left.name) - names.indexOf(right.name)
  })[0]
  return {
    label,
    status: worst.status,
    ok: worst.status !== 'fail',
    detail: worst.message
  }
}

export function buildStyleTransferValidationCards(consistency) {
  const checks = consistency?.checks || []
  return [
    cardFromChecks(
      checks,
      ['recipient_consistency', 'kinship_consistency', 'new_name_check'],
      '人物一致',
      '未检测到人物关系冲突或新增姓名。'
    ),
    cardFromChecks(
      checks,
      ['amount_consistency', 'new_amount_check'],
      '金额一致',
      '未检测到金额新增、遗漏或数值变化。'
    ),
    cardFromChecks(
      checks,
      ['place_consistency', 'new_place_check'],
      '地点一致',
      '未检测到地点新增、遗漏或替换。'
    ),
    cardFromChecks(
      checks,
      [
        'remittance_expression',
        'new_date_check',
        'study_instruction_consistency'
      ],
      '生成边界',
      '未检测到输入之外的新事件，必要的寄递与嘱托表达已核验。'
    )
  ]
}
