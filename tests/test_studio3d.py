"""Dependency-free tests for the BEAN 3D Studio inference bridge."""
import base64
import struct
import unittest
from bean.studio3d.server import decode_image, obj_to_binary_stl, read_obj


class TestStudio3D(unittest.TestCase):
    def test_triangle_obj_conversion_mm(self):
        source = "v 0 0 0\nv 1 0 0\nv 0 2 0\nf 1 2 3\n"
        output, count = obj_to_binary_stl(source, 100)
        self.assertEqual(count, 1)
        self.assertEqual(len(output), 134)
        self.assertEqual(struct.unpack_from("<I", output, 80)[0], 1)
        xyz = [struct.unpack_from("<3f", output, 84 + 12 + p * 12) for p in range(3)]
        self.assertAlmostEqual(max(v[1] for v in xyz) - min(v[1] for v in xyz), 100)
        self.assertAlmostEqual(min(v[2] for v in xyz), 0)

    def test_polygon_triangulation(self):
        vertices, faces = read_obj("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n")
        self.assertEqual(len(vertices), 4)
        self.assertEqual(faces, [(0, 1, 2), (0, 2, 3)])

    def test_negative_indices(self):
        _, faces = read_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n")
        self.assertEqual(faces, [(0, 1, 2)])

    def test_invalid_face_reference(self):
        with self.assertRaises(ValueError):
            read_obj("v 0 0 0\nf 1 2 3\n")

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            obj_to_binary_stl("v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", 100)
        with self.assertRaises(ValueError):
            obj_to_binary_stl("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", float("inf"))

    def test_png_signature(self):
        tiny = b"\x89PNG\r\n\x1a\n" + b"sample"
        data, ext = decode_image("data:image/png;base64," + base64.b64encode(tiny).decode())
        self.assertEqual(data, tiny)
        self.assertEqual(ext, ".png")

    def test_disguised_image_rejected(self):
        with self.assertRaises(ValueError):
            decode_image("data:image/png;base64," + base64.b64encode(b"not a png").decode())


if __name__ == "__main__":
    unittest.main()
