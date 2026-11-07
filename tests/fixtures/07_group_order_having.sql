SELECT
  dept,
  COUNT(*)
FROM employees
GROUP BY dept
HAVING COUNT(*) > 5
ORDER BY dept ASC
