"""Parsing and VarSet mutation logic for QuickVarSet.

This module does not import Qt.  It can therefore be exercised with
FreeCADCmd and keeps UI errors separate from document mutations.
"""

import re

import FreeCAD as App


DEFAULT_GROUP_NAME = "Base"

# These properties are supplied by App::VarSet itself.  They are not user
# variables and must not be offered as formula candidates by this addon.
SYSTEM_PROPERTY_NAMES = frozenset(
    {
        "ExpressionEngine",
        "Group",
        "Label",
        "Label2",
        "Name",
        "Visibility",
    }
)

UNIT_PROPERTY_TYPES = {
    "Angle": "App::PropertyAngle",
    "Area": "App::PropertyArea",
    "Volume": "App::PropertyVolume",
    "Mass": "App::PropertyMass",
    "TimeSpan": "App::PropertyTime",
    "Velocity": "App::PropertyVelocity",
    "Acceleration": "App::PropertyAcceleration",
    "Force": "App::PropertyForce",
    "Pressure": "App::PropertyPressure",
    "Energy": "App::PropertyWork",
    "Power": "App::PropertyPower",
    "Temperature": "App::PropertyTemperature",
    "Frequency": "App::PropertyFrequency",
    "ElectricCurrent": "App::PropertyElectricCurrent",
    "ElectricPotential": "App::PropertyElectricPotential",
    "ElectricalCapacitance": "App::PropertyElectricalCapacitance",
    "ElectricalInductance": "App::PropertyElectricalInductance",
    "ElectricalConductance": "App::PropertyElectricalConductance",
    "ElectricalResistance": "App::PropertyElectricalResistance",
    "ElectricCharge": "App::PropertyElectricCharge",
    "Density": "App::PropertyDensity",
}


class QuickVarSetError(Exception):
    """An expected, user-facing QuickVarSet operation error."""


class QuickVarSetCancelled(Exception):
    """The user declined a confirmation dialog."""


def _log(logger, level, message):
    if logger is not None:
        logger(level, message)


def property_exists(obj, name):
    return name in obj.PropertiesList


def is_system_property(name):
    return name in SYSTEM_PROPERTY_NAMES


def get_user_properties(obj):
    """Return properties that can represent user variables."""

    return [
        name
        for name in obj.PropertiesList
        if not is_system_property(name)
    ]


def get_existing_groups(obj):
    """Return user-property groups in the order used by the VarSet."""

    groups = []

    for name in get_user_properties(obj):
        try:
            group = obj.getGroupOfProperty(name)
        except Exception:
            group = None

        if group and group not in groups:
            groups.append(group)

    return groups


def get_property_expression(obj, name):
    try:
        expression = obj.getExpression(name)
    except Exception:
        return None

    return expression or None


def get_property_unit_type(obj, name):
    """Return a property's unit dimension, or None for non-quantities."""

    try:
        prop = obj.getPropertyByName(name)
        return prop.Unit.Type
    except Exception:
        return None


def get_quantity_value(quantity):
    try:
        return quantity.Value
    except Exception:
        return quantity.getValue()


def is_negative_quantity(quantity):
    return get_quantity_value(quantity) < 0


def get_new_property_type(quantity):
    """Return the property class needed for a new quantity."""

    unit_type = quantity.Unit.Type

    if unit_type == "Length":
        if is_negative_quantity(quantity):
            return "App::PropertyDistance"
        return "App::PropertyLength"

    return UNIT_PROPERTY_TYPES.get(unit_type, "App::PropertyQuantity")


def _normalize_group(group):
    group = group.strip().replace(" ", "_")

    if not group:
        raise QuickVarSetError("Group name cannot be empty.")

    return group


def _split_group_and_name(text):
    if "/" not in text:
        return None, text.strip()

    group, name = text.split("/", 1)
    group = _normalize_group(group)
    return group, name.strip()


def _syntax_error():
    return QuickVarSetError(
        "Syntax must be either:\n"
        "  Name=Value\n"
        "or\n"
        "  Name Value\n"
        "Optional group prefixes use Group/Name."
    )


def parse_input(text):
    """Parse the supported QuickVarSet input forms.

    Group detection is limited to the name portion.  This is important for
    values such as ``10 m/s``: the slash belongs to the unit, not a group.
    """

    text = text.strip()

    if not text:
        raise QuickVarSetError("Input is empty.")

    group_name = None

    if "=" in text:
        raw_name, value_text = text.split("=", 1)
        group_name, raw_name = _split_group_and_name(raw_name.strip())
        value_text = value_text.strip()
    else:
        parts = text.split(None, 1)

        if len(parts) != 2:
            if parts and parts[0].endswith("/"):
                group = _normalize_group(parts[0][:-1])
                raise QuickVarSetError(
                    f"Group '{group}' selected. "
                    "Enter a parameter after '/'."
                )
            raise _syntax_error()

        first, remainder = parts

        if first.endswith("/"):
            group_name = _normalize_group(first[:-1])
            name_parts = remainder.split(None, 1)

            if len(name_parts) != 2:
                raise _syntax_error()

            raw_name, value_text = name_parts
        elif "/" in first:
            group_name, raw_name = _split_group_and_name(first)
            value_text = remainder.strip()
        else:
            raw_name = first
            value_text = remainder.strip()

    if not raw_name:
        raise QuickVarSetError("Parameter name cannot be empty.")

    if not value_text:
        raise QuickVarSetError("Parameter value cannot be empty.")

    name = raw_name.replace(" ", "_")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise QuickVarSetError(
            f"Invalid parameter name '{raw_name}'. Use letters, numbers, "
            "and underscores, with a letter or underscore first."
        )

    if is_system_property(name):
        raise QuickVarSetError(
            f"'{name}' is a built-in VarSet property and cannot be used "
            "as a QuickVarSet variable."
        )

    try:
        quantity = App.Units.Quantity(value_text)
    except Exception as err:
        raise QuickVarSetError(
            f"Cannot parse value '{value_text}': {err}"
        ) from err

    return group_name, name, value_text, quantity


def _set_property_group(obj, name, group):
    try:
        obj.setGroupOfProperty(name, group)
        actual_group = obj.getGroupOfProperty(name)
    except Exception as err:
        raise QuickVarSetError(
            f"Could not move property '{name}' to group '{group}': {err}"
        ) from err

    if actual_group != group:
        raise QuickVarSetError(
            f"Could not move property '{name}' to group '{group}'. "
            f"FreeCAD reports group '{actual_group}'."
        )


def _add_property(obj, property_type, name, group):
    try:
        obj.addProperty(property_type, name, group, "")
    except Exception as err:
        raise QuickVarSetError(
            f"FreeCAD could not create '{name}' as {property_type}: {err}"
        ) from err

    if not property_exists(obj, name):
        raise QuickVarSetError(
            f"FreeCAD did not create property '{name}' even though "
            "addProperty returned."
        )

    actual_type = obj.getTypeIdOfProperty(name)

    if actual_type != property_type:
        raise QuickVarSetError(
            f"FreeCAD created '{name}' as {actual_type}, expected "
            f"{property_type}."
        )


def _assign_value(obj, name, quantity):
    try:
        setattr(obj, name, quantity)
    except Exception as err:
        raise QuickVarSetError(
            f"FreeCAD could not set '{name}' to '{quantity}': {err}"
        ) from err

    try:
        actual_quantity = getattr(obj, name)
        actual_value = get_quantity_value(actual_quantity)
        expected_value = get_quantity_value(quantity)
    except Exception as err:
        raise QuickVarSetError(
            f"FreeCAD set '{name}', but QuickVarSet could not verify "
            f"the stored value: {err}"
        ) from err

    tolerance = 1e-9 * max(1.0, abs(expected_value))

    if abs(actual_value - expected_value) > tolerance:
        raise QuickVarSetError(
            f"FreeCAD stored '{name}' as '{actual_quantity}', expected "
            f"'{quantity}'."
        )


def _recreate_property(
    obj,
    name,
    property_type,
    group,
    quantity,
    old_expression,
    logger,
):
    try:
        obj.removeProperty(name)
    except Exception as err:
        raise QuickVarSetError(
            f"FreeCAD could not remove '{name}' for recreation: {err}"
        ) from err

    if property_exists(obj, name):
        raise QuickVarSetError(
            f"FreeCAD did not remove '{name}' before recreation."
        )

    _add_property(obj, property_type, name, group)
    _assign_value(obj, name, quantity)

    if old_expression:
        try:
            obj.setExpression(name, old_expression)
        except Exception as err:
            _log(
                logger,
                "warning",
                f"Could not restore expression for '{name}': {err}",
            )


def _confirm(
    confirm_change,
    name,
    current_type,
    requested_type,
    reason,
    current_group,
    requested_group,
    current_expression,
):
    if confirm_change is None:
        raise QuickVarSetError(
            "A confirmation callback is required before changing a "
            "property type."
        )

    confirmed = confirm_change(
        name,
        current_type,
        requested_type,
        reason,
        current_group,
        requested_group,
        current_expression,
    )

    if not confirmed:
        raise QuickVarSetCancelled(f"Change cancelled for '{name}'.")


def apply_input(
    doc,
    target_varset,
    text,
    default_group,
    confirm_change=None,
    logger=None,
):
    """Apply one parsed input to a VarSet and return an operation result."""

    if doc is None:
        raise QuickVarSetError("No active document found.")

    if target_varset is None:
        raise QuickVarSetError("No target VarSet was selected.")

    default_group = _normalize_group(default_group or DEFAULT_GROUP_NAME)
    group_name, name, value_text, quantity = parse_input(text)

    if group_name:
        requested_group = group_name
    else:
        requested_group = default_group

    if property_exists(target_varset, name):
        if is_system_property(name):
            raise QuickVarSetError(
                f"'{name}' is a built-in VarSet property and cannot be "
                "modified as a user variable."
            )

        try:
            existing_type = target_varset.getTypeIdOfProperty(name)
        except Exception as err:
            raise QuickVarSetError(
                f"Could not inspect existing property '{name}': {err}"
            ) from err

        existing_unit_type = get_property_unit_type(target_varset, name)

        try:
            existing_group = target_varset.getGroupOfProperty(name)
        except Exception:
            existing_group = None

        existing_group = existing_group or default_group
        requested_group = group_name or existing_group
        current_expression = get_property_expression(target_varset, name)

        same_dimension = (
            existing_unit_type is not None
            and existing_unit_type == quantity.Unit.Type
        )

        needs_negative_length_change = (
            same_dimension
            and quantity.Unit.Type == "Length"
            and is_negative_quantity(quantity)
            and existing_type == "App::PropertyLength"
        )

        if needs_negative_length_change:
            requested_type = "App::PropertyDistance"
            reason = (
                "The value is negative, but the existing PropertyLength "
                "cannot contain negative values. The property must be "
                "recreated as PropertyDistance."
            )

            _confirm(
                confirm_change,
                name,
                existing_type,
                requested_type,
                reason,
                existing_group,
                requested_group,
                current_expression,
            )

            _recreate_property(
                target_varset,
                name,
                requested_type,
                requested_group,
                quantity,
                current_expression,
                logger,
            )
            doc.recompute()

            return {
                "action": "recreated",
                "name": name,
                "value": value_text,
                "property_type": requested_type,
                "unit_type": quantity.Unit.Type,
                "group": requested_group,
            }

        if same_dimension:
            _assign_value(target_varset, name, quantity)

            if group_name and existing_group != requested_group:
                _set_property_group(
                    target_varset,
                    name,
                    requested_group,
                )

            doc.recompute()

            return {
                "action": "updated",
                "name": name,
                "value": value_text,
                "property_type": existing_type,
                "unit_type": quantity.Unit.Type,
                "group": requested_group,
            }

        requested_type = get_new_property_type(quantity)
        reason = (
            "The requested value has a different unit dimension from the "
            "existing property. The property must be recreated."
        )

        _confirm(
            confirm_change,
            name,
            existing_type,
            requested_type,
            reason,
            existing_group,
            requested_group,
            current_expression,
        )

        _recreate_property(
            target_varset,
            name,
            requested_type,
            requested_group,
            quantity,
            current_expression,
            logger,
        )
        doc.recompute()

        return {
            "action": "recreated",
            "name": name,
            "value": value_text,
            "property_type": requested_type,
            "unit_type": quantity.Unit.Type,
            "group": requested_group,
        }

    property_type = get_new_property_type(quantity)

    _add_property(target_varset, property_type, name, requested_group)
    _assign_value(target_varset, name, quantity)
    doc.recompute()

    return {
        "action": "created",
        "name": name,
        "value": value_text,
        "property_type": property_type,
        "unit_type": quantity.Unit.Type,
        "group": requested_group,
    }