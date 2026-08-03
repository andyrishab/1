from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from config import ACTIVITY_JSON, COUNTS_JSON, MOVEMENTS_JSON, load_json, save_json
from utils import append_activity, create_activity, safe_int, safe_text, utc_now


class InventoryService:
    """Handle stock count sessions and inventory lifecycle."""

    def __init__(self) -> None:
        self.path = COUNTS_JSON

    def load(self) -> List[Dict[str, Any]]:
        payload = load_json(self.path)
        return payload.get("counts", [])

    def save(self, counts: List[Dict[str, Any]]) -> None:
        save_json(self.path, {"counts": counts})

    def _next_id(self, sessions: List[Dict[str, Any]]) -> int:
        if not sessions:
            return 1
        return max(int(session.get("id", 0)) for session in sessions) + 1

    def create_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sessions = self.load()
        session = copy.deepcopy(payload)
        session["id"] = self._next_id(sessions)
        session["status"] = "active"
        session["type"] = safe_text(session.get("type", "full_count"))
        session["warehouse"] = safe_text(session.get("warehouse", "Main"))
        session["location"] = safe_text(session.get("location", ""))
        session["category"] = safe_text(session.get("category", ""))
        session["brand"] = safe_text(session.get("brand", ""))
        session["items"] = []
        session["notes"] = safe_text(session.get("notes", ""))
        session["created_at"] = utc_now()
        session["updated_at"] = utc_now()
        sessions.append(session)
        self.save(sessions)
        ActivityService().log_action(
            "count_session_created",
            f"Session {session['id']} created: {session.get('name', 'Unnamed')} ({session['type']})",
        )
        return session

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        for session in self.load():
            if int(session.get("id", 0)) == int(session_id):
                return session
        return None

    def update_session(self, session_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sessions = self.load()
        for index, session in enumerate(sessions):
            if int(session.get("id", 0)) == int(session_id):
                updated = {**session, **payload}
                updated["status"] = safe_text(updated.get("status", session.get("status", "active")))
                updated["updated_at"] = utc_now()
                sessions[index] = updated
                self.save(sessions)
                ActivityService().log_action(
                    "count_session_updated",
                    f"Session {session_id} updated: status={updated['status']}",
                )
                return updated
        return None

    def complete_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"status": "completed"})

    def pause_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"status": "paused"})

    def resume_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"status": "active"})

    def cancel_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"status": "cancelled"})

    def add_count_item(self, session_id: int, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sessions = self.load()
        for index, session in enumerate(sessions):
            if int(session.get("id", 0)) == int(session_id):
                row = {
                    "item_id": len(session.get("items", [])) + 1,
                    "product_id": int(item.get("product_id", 0)),
                    "product_name": safe_text(item.get("product_name")),
                    "barcode": safe_text(item.get("barcode")),
                    "sku": safe_text(item.get("sku")),
                    "expected_quantity": safe_int(item.get("expected_quantity", 0)),
                    "counted_quantity": safe_int(item.get("counted_quantity", 0)),
                    "difference": safe_int(item.get("counted_quantity", 0)) - safe_int(item.get("expected_quantity", 0)),
                    "status": safe_text(item.get("status", "pending")),
                    "notes": safe_text(item.get("notes", "")),
                    "updated_at": utc_now(),
                }
                session_items = list(session.get("items", []))
                session_items.append(row)
                session["items"] = session_items
                session["updated_at"] = utc_now()
                sessions[index] = session
                self.save(sessions)
                ActivityService().log_action(
                    "count_item_added",
                    f"Added count item to session {session_id}: product_id={row['product_id']} expected={row['expected_quantity']} counted={row['counted_quantity']}",
                )
                return row
        return None

    def update_count_item(self, session_id: int, item_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sessions = self.load()
        for s_index, session in enumerate(sessions):
            if int(session.get("id", 0)) == int(session_id):
                items = list(session.get("items", []))
                for i_index, item in enumerate(items):
                    if int(item.get("item_id", 0)) == int(item_id):
                        updated = {**item, **payload}
                        updated["counted_quantity"] = safe_int(updated.get("counted_quantity", item.get("counted_quantity", 0)))
                        updated["expected_quantity"] = safe_int(updated.get("expected_quantity", item.get("expected_quantity", 0)))
                        updated["difference"] = updated["counted_quantity"] - updated["expected_quantity"]
                        updated["status"] = safe_text(updated.get("status", "pending"))
                        updated["updated_at"] = utc_now()
                        items[i_index] = updated
                        session["items"] = items
                        session["updated_at"] = utc_now()
                        sessions[s_index] = session
                        self.save(sessions)
                        ActivityService().log_action(
                            "count_item_updated",
                            f"Updated count item {item_id} in session {session_id}: counted={updated['counted_quantity']} diff={updated['difference']}",
                        )
                        return updated
        return None

    def list_sessions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sessions = self.load()
        if status:
            return [session for session in sessions if safe_text(session.get("status")).lower() == status.lower()]
        return sessions

    def session_metrics(self, session_id: int) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {}
        items = list(session.get("items", []))
        total_items = len(items)
        counted = sum(item.get("counted_quantity", 0) for item in items)
        expected = sum(item.get("expected_quantity", 0) for item in items)
        variance = counted - expected
        completed = sum(1 for item in items if item.get("status") == "completed")
        pending = total_items - completed
        return {
            "name": session.get("name", ""),
            "status": session.get("status", ""),
            "total_items": total_items,
            "expected_quantity": expected,
            "counted_quantity": counted,
            "variance": variance,
            "completed_items": completed,
            "pending_items": pending,
        }


class MovementService:
    """Track stock movement events for inventory operations."""

    def __init__(self) -> None:
        self.path = MOVEMENTS_JSON

    def load(self) -> List[Dict[str, Any]]:
        payload = load_json(self.path)
        return payload.get("movements", [])

    def save(self, movements: List[Dict[str, Any]]) -> None:
        save_json(self.path, {"movements": movements})

    def _next_id(self, movements: List[Dict[str, Any]]) -> int:
        if not movements:
            return 1
        return max(int(movement.get("id", 0)) for movement in movements) + 1

    def record_movement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        movements = self.load()
        movement = copy.deepcopy(payload)
        movement["id"] = self._next_id(movements)
        movement["type"] = safe_text(movement.get("type", "adjustment"))
        movement["product_id"] = int(movement.get("product_id", 0))
        movement["quantity"] = safe_int(movement.get("quantity", 0))
        movement["warehouse_from"] = safe_text(movement.get("warehouse_from", ""))
        movement["warehouse_to"] = safe_text(movement.get("warehouse_to", ""))
        movement["reason"] = safe_text(movement.get("reason", ""))
        movement["notes"] = safe_text(movement.get("notes", ""))
        movement["created_at"] = utc_now()
        movement["updated_at"] = utc_now()
        movements.append(movement)
        self.save(movements)
        ActivityService().log_action(
            "stock_movement",
            f"Movement {movement['id']} type={movement['type']} product={movement['product_id']} qty={movement['quantity']}",
        )
        return movement

    def list_movements(self, movement_type: Optional[str] = None) -> List[Dict[str, Any]]:
        movements = self.load()
        if movement_type:
            return [movement for movement in movements if safe_text(movement.get("type")).lower() == movement_type.lower()]
        return movements

    def receive_stock(self, product_id: int, quantity: int, warehouse: str = "Main", reason: str = "stock_receive") -> Dict[str, Any]:
        return self.record_movement(
            {
                "type": "receive",
                "product_id": product_id,
                "quantity": abs(quantity),
                "warehouse_to": warehouse,
                "reason": reason,
            }
        )

    def issue_stock(self, product_id: int, quantity: int, warehouse: str = "Main", reason: str = "stock_issue") -> Dict[str, Any]:
        return self.record_movement(
            {
                "type": "issue",
                "product_id": product_id,
                "quantity": -abs(quantity),
                "warehouse_from": warehouse,
                "reason": reason,
            }
        )

    def transfer_stock(self, product_id: int, quantity: int, source: str, destination: str, reason: str = "stock_transfer") -> Dict[str, Any]:
        return self.record_movement(
            {
                "type": "transfer",
                "product_id": product_id,
                "quantity": abs(quantity),
                "warehouse_from": source,
                "warehouse_to": destination,
                "reason": reason,
            }
        )

    def adjust_stock(self, product_id: int, quantity: int, reason: str = "stock_adjustment") -> Dict[str, Any]:
        return self.record_movement(
            {
                "type": "adjustment",
                "product_id": product_id,
                "quantity": quantity,
                "reason": reason,
            }
        )

    def create_movement_report(self) -> List[Dict[str, Any]]:
        return self.load()


class ActivityService:
    """Persist user activity and audit history."""

    def __init__(self) -> None:
        self.path = ACTIVITY_JSON

    def load(self) -> List[Dict[str, Any]]:
        payload = load_json(self.path)
        return payload.get("activity", [])

    def save(self, activity_log: List[Dict[str, Any]]) -> None:
        save_json(self.path, {"activity": activity_log})

    def log_action(self, action: str, details: str) -> Dict[str, Any]:
        activity_log = self.load()
        entry = create_activity(action, details)
        activity_log.append(entry)
        self.save(activity_log)
        return entry

    def list_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        activity_log = sorted(self.load(), key=lambda item: item.get("timestamp", ""), reverse=True)
        return activity_log[:limit]


def create_count_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    return InventoryService().create_session(payload)
