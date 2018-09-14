-- MySQL dump 10.13  Distrib 5.7.21, for Linux (x86_64)
--
-- Host: localhost    Database: bees_ants
-- ------------------------------------------------------
-- Server version	5.7.21-0ubuntu0.16.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `budget_vote`
--

DROP TABLE IF EXISTS `budget_vote`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `budget_vote` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `issue_num` int(11) NOT NULL,
  `amount` int(11) NOT NULL,
  `voter_gh` varchar(64) NOT NULL,
  `vote_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_issue` (`issue_num`),
  KEY `fk_voter` (`voter_gh`),
  CONSTRAINT `budget_vote_ibfk_1` FOREIGN KEY (`issue_num`) REFERENCES `issue` (`num`),
  CONSTRAINT `budget_vote_ibfk_2` FOREIGN KEY (`voter_gh`) REFERENCES `person` (`gh`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `budget_vote`
--

LOCK TABLES `budget_vote` WRITE;
/*!40000 ALTER TABLE `budget_vote` DISABLE KEYS */;
INSERT INTO `budget_vote` VALUES (1,260,2000,'lapin7','2018-01-31 00:31:05'),(3,260,1500,'dckc','2018-01-31 00:43:33'),(4,260,2200,'kitblake','2018-01-31 00:43:49');
/*!40000 ALTER TABLE `budget_vote` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dataface__modules`
--

DROP TABLE IF EXISTS `dataface__modules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataface__modules` (
  `module_name` varchar(255) NOT NULL,
  `module_version` int(11) DEFAULT NULL,
  PRIMARY KEY (`module_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dataface__modules`
--

LOCK TABLES `dataface__modules` WRITE;
/*!40000 ALTER TABLE `dataface__modules` DISABLE KEYS */;
/*!40000 ALTER TABLE `dataface__modules` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dataface__mtimes`
--

DROP TABLE IF EXISTS `dataface__mtimes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataface__mtimes` (
  `name` varchar(255) NOT NULL,
  `mtime` int(11) DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dataface__mtimes`
--

LOCK TABLES `dataface__mtimes` WRITE;
/*!40000 ALTER TABLE `dataface__mtimes` DISABLE KEYS */;
INSERT INTO `dataface__mtimes` VALUES ('budget_vote',1517359429),('dataface__modules',1517357360),('dataface__mtimes',1517357370),('dataface__preferences',1517357946),('dataface__record_mtimes',1517357403),('dataface__version',1517357360),('issue',1517357403),('issue_budget',1517359926),('person',1517359320),('reward',1517362418),('reward_vote',1517359390);
/*!40000 ALTER TABLE `dataface__mtimes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dataface__preferences`
--

DROP TABLE IF EXISTS `dataface__preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataface__preferences` (
  `pref_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `table` varchar(128) NOT NULL,
  `record_id` varchar(255) NOT NULL,
  `key` varchar(128) NOT NULL,
  `value` varchar(255) NOT NULL,
  PRIMARY KEY (`pref_id`),
  KEY `username` (`username`),
  KEY `table` (`table`),
  KEY `record_id` (`record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dataface__preferences`
--

LOCK TABLES `dataface__preferences` WRITE;
/*!40000 ALTER TABLE `dataface__preferences` DISABLE KEYS */;
/*!40000 ALTER TABLE `dataface__preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dataface__record_mtimes`
--

DROP TABLE IF EXISTS `dataface__record_mtimes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataface__record_mtimes` (
  `recordhash` varchar(32) NOT NULL,
  `recordid` varchar(255) NOT NULL,
  `mtime` int(11) NOT NULL,
  PRIMARY KEY (`recordhash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dataface__record_mtimes`
--

LOCK TABLES `dataface__record_mtimes` WRITE;
/*!40000 ALTER TABLE `dataface__record_mtimes` DISABLE KEYS */;
INSERT INTO `dataface__record_mtimes` VALUES ('11fe5832ae18d0ee10710b6959dc041b','person?gh=lapin7',1517357506),('442d1aae3beac27b0ee0ccc218c11cd7','reward_vote?id=2',1517359299),('774cbed471246e92ea535292394f2ee0','person?gh=dckc',1517359249),('e52cdd63db47bcc4044d0a04f9267d90','person?gh=kitblake',1517359320);
/*!40000 ALTER TABLE `dataface__record_mtimes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dataface__version`
--

DROP TABLE IF EXISTS `dataface__version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dataface__version` (
  `version` int(5) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dataface__version`
--

LOCK TABLES `dataface__version` WRITE;
/*!40000 ALTER TABLE `dataface__version` DISABLE KEYS */;
INSERT INTO `dataface__version` VALUES (0);
/*!40000 ALTER TABLE `dataface__version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `issue`
--

DROP TABLE IF EXISTS `issue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `issue` (
  `num` int(11) NOT NULL,
  `title` varchar(1024) NOT NULL,
  `repo` varchar(1024) NOT NULL,
  PRIMARY KEY (`num`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `issue`
--

LOCK TABLES `issue` WRITE;
/*!40000 ALTER TABLE `issue` DISABLE KEYS */;
INSERT INTO `issue` VALUES (260,'Assistance with payment process','https://github.com/rchain/Members');
/*!40000 ALTER TABLE `issue` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary table structure for view `issue_budget`
--

DROP TABLE IF EXISTS `issue_budget`;
/*!50001 DROP VIEW IF EXISTS `issue_budget`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `issue_budget` AS SELECT 
 1 AS `issue_num`,
 1 AS `title`,
 1 AS `voter_qty`,
 1 AS `voters`,
 1 AS `amount_avg`,
 1 AS `amount_effective`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `person`
--

DROP TABLE IF EXISTS `person`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `person` (
  `gh` varchar(64) NOT NULL,
  PRIMARY KEY (`gh`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `person`
--

LOCK TABLES `person` WRITE;
/*!40000 ALTER TABLE `person` DISABLE KEYS */;
INSERT INTO `person` VALUES ('dckc'),('kitblake'),('lapin7');
/*!40000 ALTER TABLE `person` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary table structure for view `reward`
--

DROP TABLE IF EXISTS `reward`;
/*!50001 DROP VIEW IF EXISTS `reward`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `reward` AS SELECT 
 1 AS `worker_gh`,
 1 AS `issue_num`,
 1 AS `title`,
 1 AS `voter_qty`,
 1 AS `voters`,
 1 AS `percent_avg`,
 1 AS `amount_avg`,
 1 AS `amount_effective`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `reward_vote`
--

DROP TABLE IF EXISTS `reward_vote`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reward_vote` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `issue_num` int(11) NOT NULL,
  `percent` int(11) NOT NULL,
  `worker_gh` varchar(64) NOT NULL,
  `voter_gh` varchar(64) NOT NULL,
  `vote_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_issue` (`issue_num`),
  KEY `fk_voter` (`voter_gh`),
  KEY `fk_worker` (`worker_gh`),
  CONSTRAINT `reward_vote_ibfk_1` FOREIGN KEY (`issue_num`) REFERENCES `issue` (`num`),
  CONSTRAINT `reward_vote_ibfk_2` FOREIGN KEY (`voter_gh`) REFERENCES `person` (`gh`),
  CONSTRAINT `reward_vote_ibfk_3` FOREIGN KEY (`worker_gh`) REFERENCES `person` (`gh`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reward_vote`
--

LOCK TABLES `reward_vote` WRITE;
/*!40000 ALTER TABLE `reward_vote` DISABLE KEYS */;
INSERT INTO `reward_vote` VALUES (1,260,50,'dckc','dckc','2018-01-31 00:41:15'),(2,260,50,'lapin7','dckc','2018-01-31 00:41:39'),(3,260,40,'lapin7','kitblake','2018-01-31 00:42:43'),(4,260,60,'lapin7','lapin7','2018-01-31 00:43:10');
/*!40000 ALTER TABLE `reward_vote` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Final view structure for view `issue_budget`
--

/*!50001 DROP VIEW IF EXISTS `issue_budget`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`dconnolly`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `issue_budget` AS select `ea`.`issue_num` AS `issue_num`,`ea`.`title` AS `title`,`ea`.`voter_qty` AS `voter_qty`,`ea`.`voters` AS `voters`,`ea`.`amount_avg` AS `amount_avg`,(case when (`ea`.`voter_qty` >= 3) then `ea`.`amount_avg` else NULL end) AS `amount_effective` from (select `bv`.`issue_num` AS `issue_num`,`i`.`title` AS `title`,count(distinct `bv`.`voter_gh`) AS `voter_qty`,group_concat(`bv`.`voter_gh` separator ', ') AS `voters`,avg(`bv`.`amount`) AS `amount_avg` from (`bees_ants`.`issue` `i` join `bees_ants`.`budget_vote` `bv` on((`bv`.`issue_num` = `i`.`num`))) group by `i`.`num`,`i`.`title`) `ea` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `reward`
--

/*!50001 DROP VIEW IF EXISTS `reward`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`dconnolly`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `reward` AS select `ea`.`worker_gh` AS `worker_gh`,`ea`.`issue_num` AS `issue_num`,`ea`.`title` AS `title`,`ea`.`voter_qty` AS `voter_qty`,`ea`.`voters` AS `voters`,`ea`.`percent_avg` AS `percent_avg`,`ea`.`amount_avg` AS `amount_avg`,(case when (`ea`.`voter_qty` >= 3) then `ea`.`amount_effective` else NULL end) AS `amount_effective` from (select `ib`.`issue_num` AS `issue_num`,`ib`.`title` AS `title`,`rv`.`worker_gh` AS `worker_gh`,count(distinct `rv`.`voter_gh`) AS `voter_qty`,group_concat(`rv`.`voter_gh` separator ', ') AS `voters`,avg(`rv`.`percent`) AS `percent_avg`,((avg(`rv`.`percent`) / 100) * `ib`.`amount_avg`) AS `amount_avg`,((avg(`rv`.`percent`) / 100) * `ib`.`amount_effective`) AS `amount_effective` from (`bees_ants`.`issue_budget` `ib` join `bees_ants`.`reward_vote` `rv` on((`rv`.`issue_num` = `ib`.`issue_num`))) group by `ib`.`issue_num`,`ib`.`title`,`rv`.`worker_gh`) `ea` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-01-30 19:50:46
