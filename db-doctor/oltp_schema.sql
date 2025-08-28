CREATE TABLE `lu_network_function` (
                                       `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'per network function id',
                                       `name` varchar(50) NOT NULL DEFAULT '' COMMENT 'name of function',
                                       `description` text NOT NULL COMMENT 'description in detail',
                                       `priority` tinyint NOT NULL DEFAULT '0' COMMENT '0 means normalnetwork function; 1 means critical one',
                                       `deprecated` tinyint NOT NULL DEFAULT '0' COMMENT '1 means deprecated function; 0 means normal function',
                                       `product` enum('UI','Ad Serving','Forecasting','BVI','Internal','VI','Log Files','International','Audience','VOD/CIP','Scenario Forecasting','RPM Partner','Stream Stitching','Scenario Testing','Client Specific','RBP','Partner Module','Transcoding','HYLDA','Partner Integrations','Insights','Revenue Management','Order Management','Scenarios','Markets','Marketplace','Partner Trading','Audience Manager','Buyer Platform','UI Redesign') NOT NULL DEFAULT 'UI',
                                       `param_description` text COMMENT 'description for parameter',
                                       `param_required` tinyint NOT NULL DEFAULT '0' COMMENT '0 means parameter is not required ; 1 means parameter is mandatory',
                                       `do_not_enable` tinyint NOT NULL DEFAULT '0' COMMENT '0 means can be enabled ; 1 means can not enabled',
                                       PRIMARY KEY (`id`),
                                       UNIQUE KEY `idx_network_function_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2078 DEFAULT CHARSET=utf8mb3 COMMENT='description of per network function';


CREATE TABLE `network` (
                           `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Describes the networks in the system.',
                           `active` tinyint(1) NOT NULL DEFAULT '1',
                           `third_party_adserver_conversion_template` varchar(4096) DEFAULT NULL COMMENT 'third party url conversion template for integration. Each company has one template format for their partner(s)',
                           `asset_group_root_node_id` bigint DEFAULT NULL COMMENT 'the special root node for the asset_group',
                           `site_section_group_root_node_id` bigint DEFAULT NULL COMMENT 'the special root node for the site_section_group',
                           `company_id` bigint NOT NULL COMMENT 'The company object for this network.',
                           `timezone_id` bigint NOT NULL COMMENT 'FK(lu_timezone.id), used for reporting and UI to display relative time againist timezone of network',
                           `report_timezone_automatic_dst_adjust` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'If the timezone profile specifies that DST is observed reporting will automatically adjust to DST if this is true. Else it iwll not. ',
                           `network_type` enum('FULL','INTERNAL') NOT NULL DEFAULT 'INTERNAL' COMMENT 'FULL means the network is MRM client. INTERNAL means the network is partner of MRM Client. ',
                           `test_mode` tinyint(1) NOT NULL DEFAULT '0' COMMENT '0 = false corresponds to network in PRODUCTION mode, 1 = TRUE corresponds to network in TEST mode',
                           `currency_id` bigint NOT NULL COMMENT 'The currency in which the network operates. ',
                           `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                           `created_at` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
                           `locale_code` varchar(20) DEFAULT NULL,
                           `name` varchar(255) NOT NULL,
                           `visible` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'visible flag for global network search in partner module',
                           `disable` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'disable flag for show/hidden in Super Admin',
                           `default_currency_id` bigint DEFAULT NULL,
                           `enable_price_awareness_3rd_party_ads` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'preferred price awareness partner flag for reseller network',
                           `ssp_buy_side_type` enum('SEAT','BUYER_PLATFORM','DEMAND_SIDE_PLATFORM','ADVERTISING_TECH_PLATFORM') DEFAULT NULL COMMENT 'NULL means this network is not related to SSP',
                           `publisher_id` bigint NOT NULL DEFAULT '0' COMMENT 'id sent as publisher id in bid request for ads.txt',
                           `client_impact` tinyint(1) DEFAULT NULL COMMENT 'whether the network has client impaction, 0 no 1 yes',
                           `is_template` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'used by New SuperAdmin, 1 means this network is a template network, user can clone it to create a new network',
                           PRIMARY KEY (`id`),
                           UNIQUE KEY `idx_network_name` (`name`),
                           KEY `fk_network_company_id` (`company_id`),
                           KEY `fk_network_timezone_id` (`timezone_id`),
                           KEY `fk_default_currency_id` (`default_currency_id`),
                           CONSTRAINT `fk_default_currency_id` FOREIGN KEY (`default_currency_id`) REFERENCES `lu_currency` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
                           CONSTRAINT `fk_network_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
                           CONSTRAINT `fk_network_timezone_id` FOREIGN KEY (`timezone_id`) REFERENCES `lu_timezone` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2003616675 DEFAULT CHARSET=utf8mb3;

CREATE TABLE `network_function` (
                                    `id` bigint NOT NULL AUTO_INCREMENT,
                                    `network_id` bigint NOT NULL COMMENT 'id in network table',
                                    `function_id` bigint NOT NULL COMMENT 'id in lu_network_function table',
                                    `parameter` varchar(1000) NOT NULL DEFAULT '' COMMENT 'parameter of the function',
                                    `created_at` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
                                    `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                    `super_admin_user_id` bigint DEFAULT NULL,
                                    PRIMARY KEY (`id`),
                                    UNIQUE KEY `idx_network_function` (`network_id`,`function_id`),
                                    KEY `idx_network_function_function` (`function_id`),
                                    CONSTRAINT `FK_network_function` FOREIGN KEY (`function_id`) REFERENCES `lu_network_function` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
                                    CONSTRAINT `FK_network_function_network_id` FOREIGN KEY (`network_id`) REFERENCES `network` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2107745459 DEFAULT CHARSET=utf8mb3 COMMENT='functions enabled per network';