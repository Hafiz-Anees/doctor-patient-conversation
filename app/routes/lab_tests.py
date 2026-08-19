"""
routes/lab_tests.py — lab test dropdown + search endpoints.
"""

from fastapi import APIRouter
from tools.lab_tests import LAB_TESTS, get_all_categories, get_tests_by_category

router = APIRouter(prefix="/lab-tests", tags=["Lab Tests"])


@router.get("/")
def get_all_lab_tests():
    grouped: dict = {}
    for test in LAB_TESTS:
        cat = test["category"]
        grouped.setdefault(cat, []).append({"code": test["code"], "name": test["name"]})
    return {
        "status": "success",
        "total":  len(LAB_TESTS),
        "categories": list(grouped.keys()),
        "tests_by_category": grouped,
    }


@router.get("/categories")
def list_categories():
    return {"categories": get_all_categories()}


@router.get("/category/{category_name}")
def tests_by_category(category_name: str):
    results = get_tests_by_category(category_name)
    if not results:
        return {"status": "not_found", "message": f"No tests in category: {category_name}"}
    return {
        "status":   "success",
        "category": category_name,
        "total":    len(results),
        "tests":    [{"code": t["code"], "name": t["name"]} for t in results],
    }


@router.get("/search/{keyword}")
def search_lab_tests(keyword: str):
    kw = keyword.lower().strip()
    results = [
        {"code": t["code"], "name": t["name"], "category": t["category"]}
        for t in LAB_TESTS
        if kw in (t["name"].lower() + " " + " ".join(t.get("aliases", [])))
    ]
    if not results:
        return {"status": "not_found", "message": f"No test found for: {keyword}"}
    return {"status": "success", "total": len(results), "results": results}
