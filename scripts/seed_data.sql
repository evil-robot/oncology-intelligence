-- Seed sample data for Pediatric Oncology Intelligence
-- Run this after init_db.sql

-- Insert clusters
INSERT INTO clusters (id, name, centroid_x, centroid_y, centroid_z, color, size, term_count) VALUES
(1, 'Leukemia / ALL / AML', -2.5, 1.2, 0.8, '#6366f1', 1.4, 12),
(2, 'Brain Tumors / DIPG', 1.8, 2.1, -1.2, '#ec4899', 1.2, 10),
(3, 'Neuroblastoma / Solid Tumors', 2.2, -1.5, 1.5, '#14b8a6', 1.1, 9),
(4, 'Treatment / Chemotherapy', -1.0, -2.2, -0.5, '#f59e0b', 1.3, 11),
(5, 'Support / Resources', -3.0, -0.5, 2.0, '#8b5cf6', 1.0, 8),
(6, 'Survivorship / Late Effects', 0.5, 0.3, -2.5, '#22c55e', 0.9, 7)
ON CONFLICT (id) DO NOTHING;

-- Insert search terms
INSERT INTO search_terms (id, term, normalized_term, category, subcategory, x, y, z, cluster_id) VALUES
(1, 'childhood leukemia', 'childhood leukemia', 'diagnosis', 'leukemia', -2.3, 1.0, 0.6, 1),
(2, 'acute lymphoblastic leukemia children', 'acute lymphoblastic leukemia children', 'diagnosis', 'leukemia', -2.7, 1.4, 0.9, 1),
(3, 'ALL in children', 'all in children', 'diagnosis', 'leukemia', -2.4, 1.1, 1.0, 1),
(4, 'acute myeloid leukemia pediatric', 'acute myeloid leukemia pediatric', 'diagnosis', 'leukemia', -2.6, 1.3, 0.5, 1),
(5, 'AML children', 'aml children', 'diagnosis', 'leukemia', -2.5, 1.5, 0.7, 1),
(6, 'pediatric brain tumor', 'pediatric brain tumor', 'diagnosis', 'brain_tumor', 1.6, 2.0, -1.0, 2),
(7, 'childhood brain cancer', 'childhood brain cancer', 'diagnosis', 'brain_tumor', 1.9, 2.2, -1.3, 2),
(8, 'medulloblastoma', 'medulloblastoma', 'diagnosis', 'brain_tumor', 2.0, 2.3, -1.1, 2),
(9, 'DIPG', 'dipg', 'diagnosis', 'brain_tumor', 1.7, 1.9, -1.4, 2),
(10, 'diffuse intrinsic pontine glioma', 'diffuse intrinsic pontine glioma', 'diagnosis', 'brain_tumor', 1.8, 2.4, -1.2, 2),
(11, 'neuroblastoma', 'neuroblastoma', 'diagnosis', 'solid_tumor', 2.0, -1.3, 1.4, 3),
(12, 'wilms tumor', 'wilms tumor', 'diagnosis', 'solid_tumor', 2.3, -1.6, 1.6, 3),
(13, 'rhabdomyosarcoma', 'rhabdomyosarcoma', 'diagnosis', 'solid_tumor', 2.4, -1.4, 1.3, 3),
(14, 'osteosarcoma children', 'osteosarcoma children', 'diagnosis', 'solid_tumor', 2.1, -1.7, 1.7, 3),
(15, 'pediatric chemotherapy', 'pediatric chemotherapy', 'treatment', 'chemotherapy', -0.8, -2.0, -0.4, 4),
(16, 'chemo for kids', 'chemo for kids', 'treatment', 'chemotherapy', -1.1, -2.3, -0.6, 4),
(17, 'pediatric radiation therapy', 'pediatric radiation therapy', 'treatment', 'radiation', -1.2, -2.1, -0.3, 4),
(18, 'proton therapy children', 'proton therapy children', 'treatment', 'radiation', -0.9, -2.4, -0.7, 4),
(19, 'bone marrow transplant children', 'bone marrow transplant children', 'treatment', 'transplant', -1.0, -2.0, -0.5, 4),
(20, 'CAR-T therapy pediatric', 'car-t therapy pediatric', 'treatment', 'immunotherapy', -0.7, -2.5, -0.4, 4),
(21, 'childhood cancer support groups', 'childhood cancer support groups', 'support', 'community', -2.8, -0.4, 1.9, 5),
(22, 'pediatric oncology hospital', 'pediatric oncology hospital', 'support', 'facility', -3.1, -0.6, 2.1, 5),
(23, 'childrens cancer center near me', 'childrens cancer center near me', 'support', 'facility', -3.2, -0.3, 1.8, 5),
(24, 'childhood cancer financial assistance', 'childhood cancer financial assistance', 'support', 'financial', -2.9, -0.7, 2.2, 5),
(25, 'childhood cancer survivor', 'childhood cancer survivor', 'survivorship', 'general', 0.4, 0.2, -2.4, 6),
(26, 'late effects childhood cancer', 'late effects childhood cancer', 'survivorship', 'late_effects', 0.6, 0.4, -2.6, 6),
(27, 'long term effects pediatric cancer treatment', 'long term effects pediatric cancer treatment', 'survivorship', 'late_effects', 0.3, 0.1, -2.3, 6),
(28, 'childhood cancer survivor clinic', 'childhood cancer survivor clinic', 'survivorship', 'follow_up', 0.7, 0.5, -2.7, 6)
ON CONFLICT (term) DO NOTHING;

-- Insert posts
INSERT INTO posts (id, title, url, source, x, y, z, cluster_id) VALUES
(1, 'Understanding Childhood Leukemia: A Parents Guide', '#', 'curated', -2.2, 1.6, 0.4, 1),
(2, 'Latest Research in Pediatric Brain Tumors', '#', 'pubmed', 2.1, 2.5, -0.9, 2),
(3, 'Neuroblastoma Treatment Options 2024', '#', 'curated', 2.5, -1.2, 1.8, 3),
(4, 'Managing Chemotherapy Side Effects in Children', '#', 'internal', -0.6, -1.8, -0.2, 4),
(5, 'Finding Support: Resources for Families', '#', 'curated', -3.3, -0.2, 2.3, 5)
ON CONFLICT (id) DO NOTHING;

-- Insert geographic regions
INSERT INTO geographic_regions (geo_code, name, level, latitude, longitude, population, svi_overall) VALUES
('US-CA', 'California', 'state', 36.116203, -119.681564, 39538223, 0.52),
('US-TX', 'Texas', 'state', 31.054487, -97.563461, 29145505, 0.58),
('US-NY', 'New York', 'state', 42.165726, -74.948051, 20201249, 0.48),
('US-FL', 'Florida', 'state', 27.766279, -81.686783, 21538187, 0.55),
('US-IL', 'Illinois', 'state', 40.349457, -88.986137, 12812508, 0.51),
('US-PA', 'Pennsylvania', 'state', 40.590752, -77.209755, 13002700, 0.49),
('US-OH', 'Ohio', 'state', 40.388783, -82.764915, 11799448, 0.54),
('US-GA', 'Georgia', 'state', 33.040619, -83.643074, 10711908, 0.57)
ON CONFLICT (geo_code) DO NOTHING;

-- Reset sequences
SELECT setval('clusters_id_seq', (SELECT MAX(id) FROM clusters));
SELECT setval('search_terms_id_seq', (SELECT MAX(id) FROM search_terms));
SELECT setval('posts_id_seq', (SELECT MAX(id) FROM posts));

-- Confirmation
SELECT 'Sample data seeded successfully!' as status;
SELECT COUNT(*) as cluster_count FROM clusters;
SELECT COUNT(*) as term_count FROM search_terms;
SELECT COUNT(*) as post_count FROM posts;
SELECT COUNT(*) as region_count FROM geographic_regions;
