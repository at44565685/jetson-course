# -*- coding: utf-8 -*-
"""不需要 RealSense 相機的幾何與量測自我測試。"""
import unittest
import numpy as np
from jetson_d435i_measure import (
    fit_table_plane, TablePlane, vertices_to_xyz, create_foreground_mask,
    measure_masked_objects, clip_roi,
)


class GeometryTests(unittest.TestCase):
    def test_table_plane_and_height(self):
        x, y = np.meshgrid(np.linspace(-.30, .30, 50), np.linspace(-.20, .20, 30))
        points = np.column_stack([x.ravel(), y.ravel(), np.full(x.size, .8)])
        plane = fit_table_plane(points, tolerance_m=.003, iterations=30, min_inlier_ratio=.7)
        self.assertAlmostEqual(abs(plane.normal[2]), 1.0, places=4)
        elevated = np.array([[.01, .02, .73]])
        self.assertAlmostEqual(plane.heights(elevated)[0], .07, places=4)

    def test_measure_cuboid_top(self):
        # 製造 320x240 像素的單一桌面，上面有 120x80 像素的矩形工件頂面
        H, W = 240, 320
        ys, xs = np.mgrid[0:H,0:W]
        fx, fy, cx, cy = 290, 290, W/2, H/2
        depth = np.full((H,W), 0.8, dtype=np.float64)
        depth[80:160,100:220] = 0.73
        pts = np.stack(((xs-cx)*depth/fx, (ys-cy)*depth/fy, depth),axis=-1)
        plane = TablePlane(np.array([0,0,.8]),np.array([0,0,-1]))
        roi = (15, 15, W-30, H-30)
        mask, heights = create_foreground_mask(pts,plane,roi, .008,.2)
        results, clean = measure_masked_objects(pts,plane,mask,heights,roi,
                    min_area_px=100,min_points=100,max_objects=3,
                    kernel_size=3,height_percentile=95)
        self.assertEqual(len(results),1)
        obj = results[0]
        # 預期頂面長寬 = 120*0.73/290 約 302 mm，80*0.73/290 約 201 mm
        self.assertTrue(290 < obj['length_mm'] < 310, obj)
        self.assertTrue(190 < obj['width_mm'] < 210, obj)
        self.assertAlmostEqual(obj['height_mm'],70.0,delta=.1)

    def test_roi_and_vertices_conversion(self):
        self.assertEqual(clip_roi((1,1,30,30), 100,100),(1,1,30,30))
        # 與 RealSense pointcloud 類似的結構化頂點陣列
        raw=np.array([(1.0,2.0,3.0),(4.0,5.0,6.0)],
                 dtype=[('x','f4'),('y','f4'),('z','f4')])
        xyz=vertices_to_xyz(raw, 1,2)
        self.assertEqual(xyz.shape,(1,2,3))
        self.assertAlmostEqual(float(xyz[0,1,2]),6.0)


if __name__=='__main__':
    unittest.main()
