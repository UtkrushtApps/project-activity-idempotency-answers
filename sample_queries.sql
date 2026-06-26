SELECT client_event_id, count(*) AS activity_rows
FROM activities
WHERE client_event_id IS NOT NULL
GROUP BY client_event_id
HAVING count(*) > 1
ORDER BY activity_rows DESC, client_event_id;

SELECT pm.project_id, pm.user_id, u.display_name, pm.unread_count
FROM project_members pm
JOIN users u ON u.id = pm.user_id
WHERE pm.project_id = '11111111-1111-1111-1111-111111111111'
ORDER BY u.display_name;

SELECT p.id AS project_id, p.name, pat.total_events, count(a.id) AS actual_activity_rows
FROM projects p
JOIN project_activity_totals pat ON pat.project_id = p.id
LEFT JOIN activities a ON a.project_id = p.id
GROUP BY p.id, p.name, pat.total_events
ORDER BY p.name;
