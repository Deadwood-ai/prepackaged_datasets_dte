**Framework for prepackaged datasets for deadtrees.earth** 

**Purpose:**   
Prepackaged datasets should provide easy access to preprocessed subsets of the database without any API knowledge or API use, reducing entry barrier and API load. Each dataset has one specific goal in mind. Prepackaged datasets should be of use to a wide audience as they are expensive to define, store and generate. These datasets are separate from those that are the output of papers.

**Prepackaged datasets should be:** 

* fully reproducible  
* automatically derivable from data present and standardized in the database (supabase \+ COG storage \+ whatever will come)  
* Rerun at a regular interval and automatically expand. E.g. 3 months or 6 months, without active maintenance  
* be downloadable through http with one click on the website  
* each instance/version is immutable, thus distributable through different channels / mirrors  
* restricted to datasets that are open as CC-BY and public  
* separate package that interacts with supabase

**Properties all *dataset definition*:**  
This could be a supabase table. Frontend could exactly show this list in a pretty manner and its instances (generated packages, see below).

* *name:* unique identifier, e.g. rgb-tiles-raw-512  
* *user-description:* (or scope/goal) user-facing description of the dataset, e.g. all RGB good quality tiles   
* *technical-description*: precisely defining what this dataset contains, e.g., this dataset contains all non-overlapping RGB tiles of 512px size within the aoi of each dataset, \<10cm resolution as filter, audit needs to have passed / aoi needs to be there location information (for tiles).  
* *code:* link to the python file that produces the package at the respective commit, e.g. directly linking to a file in the backend repo https://github.com/Deadwood-ai/deadtrees-backend or can be separate repository that is called in the backend or run elsewhere

**Additional properties of *generated packages*:**  
Could be another supabase table, that has "name" from dataset definition as foreign key. This metadata is specific to each generated package and likely changes with each version.

* *version\_number:* could simply be the date of creation, 2025.4.15  
* *known\_issues:* this leaves space for listing issues with this specific generated dataset, reported by users or self-reported  
* *list of used dataset ids:* linking back to all the dataset that were fully or partially used to generate this dataset  
* *dois*: DOIs that are required to be cited when this dataset is used. This includes our own database paper, as well all DOI of all published datasets (use doi attribute from dataset table).

Each generated package should also come with a **metadata table** that includes metadata for each used dataset at the time of export. The format and columns of the metadata file should be identical across all generated packages of all types. Suggested columns for metadata export (already exactly in v2\_datasets supabase table): *id, authors, acquisition date (year, month, day), additional\_information, citation\_doi, bbox, biome\_name, in-seaons-probability*

**Potential file formats of generated packages (TBD):** 

* in general zip. or better ideas?   
* image patches: individual .tif / .npy is not really usable at scale. Need to research other widely used options, e.g. training shards.   
* labels \- vector: geopackage (identical to frontend export)  
* label \- raster: identical to image patch   
* sentinel data: zarr (TBD)

| name  | user-description | technical-description |
| :---- | :---- | :---- |
| tree-cover-drone-global | Export of all tree cover polygons derived from drone orthophotos. Can be used for upscaling or validation of coarse resolution satellite based products.  | All tree cover polygons cropped to their AOI of audited datasets, where segmentation audit quality was great or okay. One unified geopackage. During generation it uses the best available tree cover for each dataset (v\_export\_polygon\_candidates). Also includes respective AOI. |
| standing-deadwood-drone-global | Export of all standing deadwood cover polygons derived from drone orthophotos, excluding out-of-season observations. Can be used for upscaling or validation of coarse resolution satellite based products.   | Identical to tree-cover-drone-global, but for standing deadwood layer with additional filter: for tropical, filter by phenology indicator, outside tropics rely on phenology audit attribute. Identical filter used for sentinel-upscaling paper.  |
| image-tiles-1024 | All non-overlapping image tiles. Useful for unsupervised pretraining.  | Tiled dataset of patch size 1024, non-overlapping. Audit needs to have passed, but segmentation output is not relevant. Patches should be fully contained with AOI. No nodata pixels within tiles. |
| image-labels-tree-deadwood | Balanced dataset of image tiles and associated standing deadwood rasters and tree cover rasters. | Uses datasets where segmentation quality for both tree cover and standing deadwood cover is great or ok. Contains rgb image patches size 1024, stride 512, with standing deadwood raster and tree cover raster derived from polygons. Is balanced (orthophoto and region caps), i.e., can be directly used for model training with random sampling.  |
|  |  |  |

