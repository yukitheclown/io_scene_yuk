import os
import struct
import shutil
import zlib
import bpy
import mathutils
import bpy_extras.io_utils

def GetMesh(obj, context, GLOBAL_MATRIX):

	mesh = None

	try:
		mesh = obj.to_mesh()
	except RuntimeError:
		return

	# if GLOBAL_MATRIX:
	# 	mesh.transform(GLOBAL_MATRIX * obj.matrix_world)
	# else:
		mesh.transform(obj.matrix_world)

	import bmesh
	bm = bmesh.new()
	bm.from_mesh(mesh)
	bmesh.ops.triangulate(bm, faces=bm.faces)
	bm.to_mesh(mesh)
	bm.free()

	return mesh


def WriteTexture(out, image):

	data = bytearray(image.size[0] * image.size[1] * image.channels)

	out += struct.pack("<iii", image.size[0], image.size[1], image.channels)

	# pixels = list(image.pixels)

	# for k in range(0, image.size[1] * image.size[0]):

	# 	index = k*image.channels

	# 	for m in range(0, image.channels):
	# 		data[index+m] = int(pixels[index+m] * 0xFF) & 0xFF

	# out += zlib.compress(data, 9)[2:-4]

	out += bytes(map(int, [0xFF * i for i in image.pixels]))

	# out += data

	# out += zlib.compress(bytes(map(int, image.pixels)), 9)[2:-4]

def WriteFile(out, context, bones, GLOBAL_MATRIX=None):

	selected = context.selected_objects[0]

	mesh = GetMesh(selected, context, GLOBAL_MATRIX)

	uvLayer = mesh.uv_layers.active	.data[:]


	out += struct.pack("<i", len(mesh.materials))

	images = []
	topImageIndex = 0
	imagesMap = {}

	for mat in mesh.materials:

		texIndex = None
		normTexIndex = None



		out += struct.pack("<i", texIndex or 0)
		out += struct.pack("<i", normTexIndex or 0)

		color = mat.diffuse_color

		out += struct.pack("<4f", color[0], color[1], color[2], 1)
		out += struct.pack("<4f", mat.specular_color[0], mat.specular_color[1], mat.specular_color[2], mat.specular_intensity)


	out += struct.pack("<i", len(images))

	for image in images:
		WriteTexture(out, image)


	faces = [(index, face) for index, face in enumerate(mesh.polygons)]
	faces.sort(key=lambda face: face[1].material_index)
	materialElements = [[] for i in range(0, len(mesh.materials))]

	mesh.calc_normals_split()
	verts = mesh.vertices
	loops = mesh.loops

	vertMap = {}
	uniquePacked = []
	topElementIndex = 0


	for fIndex, face in faces:

		fV = [(vI, vIndex, lIndex) for vI, (vIndex, lIndex) in enumerate(zip(face.vertices, face.loop_indices))]

		v1 = mathutils.Vector(verts[fV[0][1]].co)
		v2 = mathutils.Vector(verts[fV[1][1]].co)
		v3 = mathutils.Vector(verts[fV[2][1]].co)

		uv1 = mathutils.Vector(uvLayer[fV[0][2]].uv)
		uv2 = mathutils.Vector(uvLayer[fV[1][2]].uv)
		uv3 = mathutils.Vector(uvLayer[fV[2][2]].uv)

		edge1 = v2 - v1
		edge2 = v3 - v1

		uvEdge1 = uv2 - uv1
		uvEdge2 = uv3 - uv1

		bitangent = mathutils.Vector()

		tangent = mathutils.Vector()

		mul = uvEdge1.x * uvEdge2.y - uvEdge2.x * uvEdge1.y
		
		if mul != 0:

			mul = 1.0 / mul
		
			tangent = mul * ((edge1 * uvEdge2.y) - (edge2 * uvEdge1.y))
			bitangent = mul * ((edge1 * -uvEdge2.x) + (edge2 * uvEdge1.x))

			tangent.normalize()
			bitangent.normalize()
	

		for vI, v, li in fV:

			normal = mathutils.Vector(loops[li].normal)

			sign = 1
	
			if normal.cross(tangent).dot(bitangent) > 0.0:
				sign = -1

			ctangent = tangent - tangent.dot(normal) * normal
			ctangent.normalize()

			# fix for now elements thrown off by other values
			packed = (v, (0, 0),
				(1, 1, 1),
				(1, 1, 1, 1))

			# packed = (v, (uvLayer[li].uv[0], uvLayer[li].uv[1]),
			# 	(normal.x, normal.y, normal.z),
			# 	(ctangent.x, ctangent.y, ctangent.z, sign))

			val = vertMap.get(packed)
			
			if val is None:
				vertMap[packed] = val = topElementIndex
				uniquePacked.append(packed)
				topElementIndex += 1

			if materialElements[face.material_index] is None:
				materialElements[face.material_index] = []
			
			materialElements[face.material_index].append(val)


	out += struct.pack("<i", len(uniquePacked))

	for packed in uniquePacked:

		out += struct.pack("<3f", verts[packed[0]].co[0], verts[packed[0]].co[1], verts[packed[0]].co[2])
		out += struct.pack("<2f", packed[1][0], packed[1][1])
		out += struct.pack("<3f", packed[2][0], packed[2][1], packed[2][2])
		out += struct.pack("<4f", packed[3][0], packed[3][1], packed[3][2], packed[3][3])

		if bones:
	
			weights = []

			if len(verts[packed[0]].groups) > 0:
				for group in verts[packed[0]].groups:
					if group.weight > 0:
						
						index = selected.vertex_groups[group.group].index

						weights.append([group.weight, index])

			if len(weights) < 4:
				for j in range(len(weights), 4):
					weights.append([0,-1])


			weights.sort(key=lambda tup: tup[0], reverse=True)

			out += struct.pack("<4f", weights[0][0], weights[1][0], weights[2][0], weights[3][0])
			out += struct.pack("<4f", weights[0][1], weights[1][1], weights[2][1], weights[3][1])


	# out += zlib.compress(out, 9)[2:-4]
	# out += data

	for i in range(0, len(materialElements)):
		if materialElements[i]:
			out += struct.pack("<i", len(materialElements[i]))
		else:
			out += struct.pack("<i", 0)

	for i in range(0, len(materialElements)):
		if materialElements[i]:
			for element in materialElements[i]:
				out += struct.pack("<i", element)


	return mesh


def WriteAnimation(out, action, armatureObj, bones, GLOBAL_MATRIX=None):

	endFrame = action.frame_range[1]

	boneKeyframes = [None] * len(armatureObj.pose.bones)

	for group in action.groups:

		index = bones.get(group.name)

		if index is None:
			continue

		if boneKeyframes[index] is None:
			boneKeyframes[index] = []

		setFrames = [False] * int(endFrame+1)

		for channel in group.channels:
			
			for keyframe in channel.keyframe_points:

				if int(keyframe.co[0]) <= endFrame:
					setFrames[int(keyframe.co[0])] = True

		bone = armatureObj.pose.bones[index]

		for i in range(0, len(setFrames)):

			if setFrames[i] is False:
				continue

			rot = list(bone.rotation_quaternion)
			pos = list(bone.location)

			for channel in group.channels:
			
				data = armatureObj.path_resolve(channel.data_path)

				if data == bone.rotation_quaternion:
					rot[channel.array_index] = channel.evaluate(i)
				elif data == bone.location:
					pos[channel.array_index] = channel.evaluate(i)

			boneKeyframes[index].append((i, pos[0], pos[1], pos[2], rot[1], rot[2], rot[3], rot[0]))


	out += struct.pack("<i", len(boneKeyframes))

	for j in range(0, len(boneKeyframes)):

		if boneKeyframes[j] is None:
			out += struct.pack("<i", 0)
			continue;

		out += struct.pack("<i", len(boneKeyframes[j]))

		for k in boneKeyframes[j]:

			out += struct.pack("<ifffffff", k[0], k[1], k[2], k[3], k[4], k[5], k[6], k[7])


def WriteSkeleton(out, context, selected, bones, mesh, GLOBAL_MATRIX=None):

	armatureObj = selected.find_armature()

	armatureMatrix = GLOBAL_MATRIX * armatureObj.matrix_world

	invBindMatrices = [mathutils.Matrix() for i in range(0, len(selected.vertex_groups))]
	relativeMatrices = [mathutils.Matrix() for i in range(0, len(selected.vertex_groups))]
	cubes = [[float("inf"), float("inf"), float("inf"),
	-float("inf"), -float("inf"), -float("inf")] for i in range(0, len(selected.vertex_groups))]

	for poseBone in armatureObj.pose.bones:

		armatureBone = poseBone.bone

		index = bones.get(armatureBone.name)

		if armatureBone.parent is None:
			relativeMatrices[index] = armatureMatrix * armatureBone.matrix_local
		else:
			parentMatrix = armatureBone.parent.matrix_local
			relativeMatrices[index] = armatureBone.matrix_local
			relativeMatrices[index] = parentMatrix.inverted() * relativeMatrices[index]
				
		invBindMatrices[index] = (armatureMatrix * armatureBone.matrix_local).inverted()


	for vert in mesh.vertices:

		if len(vert.groups) == 0:
			continue

		invMatrix = None

		mostInfluence = None

		for group in vert.groups:

			if group.weight > 0:

				index = selected.vertex_groups[group.group].index

				if invMatrix is None:
					invMatrix = invBindMatrices[index] * group.weight
				else:
					invMatrix += invBindMatrices[index] * group.weight

				if mostInfluence is None or mostInfluence[0] < group.weight:
					mostInfluence = (group.weight, index)


		if invMatrix is None:
			continue

		vertex = invMatrix * mathutils.Vector(vert.co).to_4d()

		vertex /= vertex.w

		cube = cubes[mostInfluence[1]]

		if vertex.x < cube[0]:
			cube[0] = vertex.x

		if vertex.y < cube[1]:
			cube[1] = vertex.y

		if vertex.z < cube[2]:
			cube[2] = vertex.z

		if vertex.x > cube[3]:
			cube[3] = vertex.x

		if vertex.y > cube[4]:
			cube[4] = vertex.y

		if vertex.z > cube[5]:
			cube[5] = vertex.z


	out += struct.pack("<i", len(armatureObj.pose.bones))

	for poseBone in armatureObj.pose.bones:

		armatureBone = poseBone.bone

		index = bones.get(armatureBone.name)

		parentIndex = -1
				
		if armatureBone.parent:
			parentIndex = bones.get(armatureBone.parent.name)

		pos, rot, scale = relativeMatrices[index].decompose()

		cube = cubes[bones.get(armatureBone.name)]

		cube[3] -= cube[0]
		cube[4] -= cube[1]
		cube[5] -= cube[2]

		out += struct.pack("<iifffffff", parentIndex, index, pos.x, pos.y, pos.z, rot.x, rot.y, rot.z, rot.w)
		out += struct.pack("<ffffff", cube[0], cube[1], cube[2], cube[3], cube[4], cube[5])



def Export(operator, context, filepath, globalMatrix=None, exportAnim=True, exportMesh=True):

	baseName = os.path.splitext(os.path.basename(filepath))[0]

	if bpy.ops.object.mode_set.poll():
		bpy.ops.object.mode_set(mode='OBJECT')

	selected = context.selected_objects[0]

	armatureObj = selected.find_armature()

	bones = None

	if armatureObj:
		
		bones = {}
		poseBones = armatureObj.pose.bones

		for index in range(0, len(poseBones)):
			bones[poseBones[index].bone.name] = index
			print(poseBones[index].bone.name, index)

	if exportMesh:
	
		out = bytearray()

		mesh = WriteFile(out, context, bones, globalMatrix)

		if armatureObj:
			WriteSkeleton(out, context, selected, bones, mesh, globalMatrix)

		fp = open(filepath, "wb")

		fp.write(out)

		fp.close()


	if exportAnim and armatureObj:

		out = bytearray()

		action = armatureObj.animation_data.action

		fp = open(baseName + "_" + action.name + ".anm", "wb")


		WriteAnimation(out, action, armatureObj, bones, globalMatrix)

		fp.write(out)

		fp.close()


	return {'FINISHED'}
