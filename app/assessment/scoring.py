

def calculate_priority(project: dict) -> dict:
    inspections = project.get("inspections", [])

    if not inspections:
        return {
            "priority_index": None,
            "urgency": None
        }

    latest = inspections[-1]

    images = latest.get("images", [])
    if not images:
        return {
            "priority_index": None,
            "urgency": None
        }

    # ---------------------------------------------------------
    # 1. DAMAGE SCORE — YOLO
    # ---------------------------------------------------------

    damage_scores = []

    for image in images:
        yolo = image.get("yolo", {})

        class_counts = yolo.get("class_counts", {})
        potholes = yolo.get("class_counts", {}).get("Potholes", 0)
        pothole_conf = yolo.get("pothole_top_confidence", 0)
        

        cracks = sum(
            count
            for name, count in class_counts.items()
            if "crack" in name.lower()
        )

        score = min(
            100,
            potholes * 15
            + cracks * 10
            + pothole_conf * 20
        )

        damage_scores.append(score)

    damage_score = max(damage_scores)


    # ---------------------------------------------------------
    # 2. AI CONDITION SCORE
    # ---------------------------------------------------------

    condition_scores = {
        "good": 10,
        "fair": 35,
        "poor": 70,
        "critical": 95
    }

    ai_scores = []

    for image in images:
        assessment = image.get("ai_inspection", {})
        condition = assessment.get("overall_condition")

        if condition in condition_scores:
            ai_scores.append(condition_scores[condition])

    ai_score = max(ai_scores) if ai_scores else 0


    # ---------------------------------------------------------
    # 3. CONNECTIVITY SCORE
    # ---------------------------------------------------------

    context = project.get("ai_context", {})
    connectivity = context.get("connectivity", {})

    connectivity_score = 0

    if connectivity.get("hospital"):
        connectivity_score += 30

    if connectivity.get("school"):
        connectivity_score += 15

    if connectivity.get("college"):
        connectivity_score += 15

    if connectivity.get("commercial"):
        connectivity_score += 10

    if connectivity.get("daily_commute"):
        connectivity_score += 15

    if connectivity.get("multiple_important_connections"):
        connectivity_score += 15

    connectivity_score = min(100, connectivity_score)


    # ---------------------------------------------------------
    # 4. FINAL PRIORITY INDEX
    # ---------------------------------------------------------

    priority_index = round(
        damage_score * 0.50
        + ai_score * 0.25
        + connectivity_score * 0.25
    )

    priority_index = min(100, priority_index)


    # ---------------------------------------------------------
    # 5. URGENCY
    # ---------------------------------------------------------

    if priority_index >= 85:
        urgency = "Critical"
    elif priority_index >= 70:
        urgency = "Very High"
    elif priority_index >= 50:
        urgency = "High"
    elif priority_index >= 30:
        urgency = "Moderate"
    else:
        urgency = "Low"

    return {
        "priority_index": priority_index,
        "urgency": urgency
    }