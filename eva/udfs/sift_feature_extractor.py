# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import cv2
import kornia
import numpy as np
import pandas as pd
import torch

from eva.catalog.catalog_type import NdArrayType
from eva.udfs.abstract.abstract_udf import AbstractUDF
from eva.udfs.decorators.decorators import forward, setup
from eva.udfs.decorators.io_descriptors.data_types import PandasDataframe


class SiftFeatureExtractor(AbstractUDF):
    @setup(cachable=False, udf_type="sift-feature-extractor", batchable=False)
    def setup(self):
        self.model = kornia.feature.SIFTDescriptor(100)

    @property
    def name(self) -> str:
        return "SiftFeatureExtractor"

    @forward(
        input_signatures=[
            PandasDataframe(
                columns=["data"],
                column_types=[NdArrayType.UINT8],
                column_shapes=[(None, None, 3)],
            )
        ],
        output_signatures=[
            PandasDataframe(
                columns=["features"],
                column_types=[NdArrayType.FLOAT32],
                column_shapes=[(1, 128)],
            )
        ],
    )
    def forward(self, df: pd.DataFrame) -> pd.DataFrame:
        def _forward(row: pd.Series) -> np.ndarray:
            # Prepare gray image to batched gray image within size.
            rgb_img = row[0]
            gray_img = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
            resized_gray_img = cv2.resize(
                gray_img, (100, 100), interpolation=cv2.INTER_AREA
            )
            resized_gray_img = np.moveaxis(resized_gray_img, -1, 0)
            batch_resized_gray_img = np.expand_dims(resized_gray_img, axis=0)
            batch_resized_gray_img = np.expand_dims(batch_resized_gray_img, axis=0)
            batch_resized_gray_img = batch_resized_gray_img.astype(np.float32)

            # Sift inference.
            with torch.no_grad():
                torch_feat = self.model(torch.from_numpy(batch_resized_gray_img))
                feat = torch_feat.numpy()

            # Feature reshape.
            feat = feat.reshape(1, -1)

            return feat

        ret = pd.DataFrame()
        ret["features"] = df.apply(_forward, axis=1)
        return ret
