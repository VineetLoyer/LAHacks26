; AskSafe OmegaClaw Skills — Agentverse Agent Integration
; These skills allow OmegaClaw to query AskSafe lecture analytics agents

; Confusion Monitor — check confusion levels for a lecture session
(= (asksafe-confusion $session_code)
   (py-call (asksafe_agents.check_confusion $session_code)))

; Question Clustering — cluster student questions for a session
(= (asksafe-clusters $session_code)
   (py-call (asksafe_agents.cluster_questions $session_code)))

; Insight Report — generate a full session report
(= (asksafe-report $session_code)
   (py-call (asksafe_agents.generate_report $session_code)))

; Register skills in OmegaClaw's skill system
; Add these entries to the getSkills function in src/skills.metta:
;
; ;AGENTVERSE AGENTS:
; "- Check lecture confusion levels using AskSafe Confusion Monitor: (asksafe-confusion \"SESSION_CODE\")"
; "- Cluster student questions using AskSafe Question Clustering: (asksafe-clusters \"SESSION_CODE\")"
; "- Generate lecture session report using AskSafe Insight Report: (asksafe-report \"SESSION_CODE\")"
