SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Tabellenstruktur für Tabelle `bucketlist_items`
--

CREATE TABLE IF NOT EXISTS `bucketlist_items` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `done` tinyint(1) NOT NULL DEFAULT '0',
  `contentType` varchar(255) NOT NULL DEFAULT 'bucketlist',
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `feed_items`
--

CREATE TABLE IF NOT EXISTS `feed_items` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `contentType` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `contentURL` longtext COLLATE utf8mb4_unicode_ci,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `filmlist_items`
--

CREATE TABLE IF NOT EXISTS `filmlist_items` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `done` tinyint(1) DEFAULT '0',
  `contentType` varchar(255) NOT NULL DEFAULT 'filmlist',
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `pushtokens`
--

CREATE TABLE IF NOT EXISTS `pushtokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `token` longtext DEFAULT NULL,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `moments_items`
--

CREATE TABLE IF NOT EXISTS `moments_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) COLLATE utf8mb4_bin NOT NULL,
  `date` varchar(255) COLLATE utf8mb4_bin NOT NULL,
  `contentType` varchar(255) COLLATE utf8mb4_bin NOT NULL DEFAULT 'moment',
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `sessions`
--

CREATE TABLE IF NOT EXISTS `sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_id` varchar(255) DEFAULT NULL,
  `expiration` datetime DEFAULT NULL,
  `last_login` varchar(255) DEFAULT NULL,
  `ip_addr` varchar(255) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Daten für Tabelle `sessions`
--

INSERT IGNORE INTO `sessions` (`id`, `session_id`, `expiration`, `last_login`, `ip_addr`, `user_agent`, `dateCreated`) VALUES ('1', 'setup_session', '2033-10-03 23:59:59', NULL, NULL, NULL, CURRENT_TIMESTAMP);


-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `settings`
--

CREATE TABLE IF NOT EXISTS `settings` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `option` text NOT NULL,
  `value` text NOT NULL,
  `specialvalue` text,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Daten für Tabelle `settings`
--

INSERT IGNORE INTO `settings` (`id`, `option`, `value`, `specialvalue`, `dateCreated`, `dateModified`) VALUES
(1, 'banner', 'https://fakeimg.pl/600x400?text=Banner-Image', '', '2023-03-10 15:49:59', '2023-09-30 20:00:00'),
(2, 'anniversary', '', NULL, '2023-03-10 15:57:22', '2023-10-03 20:44:58'),
(3, 'countdown', 'Countdown', '2023-01-01 00:00:00', '2023-04-01 00:00:47', '2023-10-03 18:06:14'),
(4, 'mainTitle', '', NULL, '2023-09-27 14:31:40', '2023-10-03 20:45:26'),
(5, 'setup_complete', 'false', NULL, '2023-09-29 22:10:08', '2023-10-03 21:04:29'),
(6, 'music', '', 'false', '2023-09-29 22:49:09', '2023-10-03 21:30:09'),
(7, 'userA', '', '', '2023-09-29 22:10:08', '2023-10-03 21:04:29'),
(8, 'userB', '', '', '2023-09-29 22:10:08', '2023-10-03 21:04:29'),
(9, 'relationship_status', '', NULL, '2023-09-29 22:10:08', '2023-10-03 21:04:29');


-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `sidemenu`
--

CREATE TABLE IF NOT EXISTS `sidemenu` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `custom_id` int(11),
  `menu` text NOT NULL,
  `href` text NOT NULL,
  `icon` text NOT NULL,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateModified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Daten für Tabelle `sidemenu`
--

-- Inserts


-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `users`
--

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) DEFAULT NULL,
  `password_salt` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
COMMIT;

