extends Node

const SETTLE_FRAMES := 180

func _ready() -> void:
	run_validation()

func run_validation() -> void:
	var main: Node3D = null
	for child in get_children():
		if child is Node3D:
			main = child
			break
	if main == null:
		return _fail("Main Node3D scene not found")

	var crate = main.get_node_or_null("Crate")
	if crate == null or not crate is RigidBody3D:
		return _fail("Crate RigidBody3D not found under Main")
	if crate.freeze:
		return _fail("Crate must remain a dynamic (non-frozen) RigidBody3D")
	if crate.global_position.y < 3.9:
		return _fail("Crate must keep its starting position above the Floor")

	var floor_body = main.get_node_or_null("Floor")
	if floor_body == null or not floor_body is StaticBody3D:
		return _fail("Floor StaticBody3D not found under Main")

	var camera = main.get_node_or_null("Camera3D")
	if camera == null or not camera is Camera3D:
		return _fail("Camera3D not found under Main")

	# Let the physics engine run so the crate falls and lands.
	for i in SETTLE_FRAMES:
		await get_tree().physics_frame

	var rest_y: float = crate.global_position.y
	if rest_y < 0.45 or rest_y > 0.55:
		return _fail("Crate did not come to rest on top of the Floor (y=%.2f)" % rest_y)
	if crate.linear_velocity.length() > 0.05:
		return _fail("Crate is still moving instead of resting on the Floor")

	if get_viewport().get_camera_3d() != camera:
		return _fail("Camera3D must be the active camera")
	if not camera.is_position_in_frustum(crate.global_position):
		return _fail("Crate is not inside the Camera3D view after landing")

	print("VALIDATION_PASSED: Crate lands on the Floor and is visible to the camera")
	get_tree().quit(0)

func _fail(message: String) -> void:
	print("VALIDATION_FAILED: %s" % message)
	get_tree().quit(1)
