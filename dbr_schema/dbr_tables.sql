drop table if exists trust_cert;
drop table if exists invoice_info;
drop table if exists reward_vote;
drop table if exists reward_fixed;
drop table if exists budget_vote;
drop table if exists github_users;
drop table if exists admin_settings;
drop table if exists pay_period;

drop table if exists issue;
create table issue (
  num integer primary key,
  title varchar(1024) not null,
  labels text,
  createdAt timestamp default current_timestamp,
  updatedAt timestamp default current_timestamp,
  updatedAt timestamp,
  `state` varchar(32) not null,
  repo varchar(1024) not null
) CHARACTER SET=utf8
;

DROP TABLE IF EXISTS `authorities`;
CREATE TABLE `authorities` (
  `login` varchar(18) DEFAULT NULL,
  `rating` bigint(20) DEFAULT NULL,
  `last_cert_time` datetime DEFAULT NULL,
  KEY `ix_authorities_login` (`login`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
ALTER TABLE authorities CONVERT TO CHARACTER SET utf8;

create table pay_period (
        start_date date primary key,
        end_date date not null,
        weighted boolean,
	rate float
        )
    ;

create table admin_settings (
        id integer primary key, --  auto_increment
        current_pay_period date not null,
        foreign key (current_pay_period) -- fk_admin_period
        references pay_period(start_date)
        )
    ;


CREATE TABLE `github_users` (
  `login` varchar(64) NOT NULL,
  `followers` bigint(20) DEFAULT NULL,
  `name` varchar(128)
        CHARACTER SET utf8 COLLATE utf8_general_ci
	DEFAULT NULL,
  `location` varchar(128)
        CHARACTER SET utf8 COLLATE utf8_general_ci
	DEFAULT NULL,
  `email` varchar(128)
        CHARACTER SET utf8 COLLATE utf8_general_ci
	DEFAULT NULL,
  `bio` varchar(512)
        CHARACTER SET utf8 COLLATE utf8_general_ci
	DEFAULT NULL,
  `websiteUrl` varchar(512)
         CHARACTER SET utf8 COLLATE utf8_general_ci
	 DEFAULT NULL,
  `avatarUrl` varchar(92) DEFAULT NULL,
  `permission` varchar(16) DEFAULT NULL,
  `createdAt` datetime DEFAULT NULL,
  `session_token` varchar(64) DEFAULT NULL,
  `verified_coop` bigint(20) unsigned DEFAULT NULL,
  PRIMARY KEY (`login`),
  KEY `ix_github_users_login` (`login`)
)
;
LOCK TABLES
  github_users write,
  budget_vote write,
  reward_vote write;
SET FOREIGN_KEY_CHECKS = 0;

ALTER TABLE github_users CONVERT TO CHARACTER SET utf8;
ALTER TABLE github_users set CHARACTER SET utf8;
ALTER TABLE github_users
  CHANGE COLUMN login login varchar(64) CHARACTER SET utf8 COLLATE utf8_general_ci;

create table budget_vote (
  pay_period date not null,
  issue_num integer not null,
  voter varchar(64) not null,
  amount decimal(13, 2) not null,
  vote_time timestamp not null default current_timestamp,
  primary key(pay_period, issue_num, voter),
  foreign key (pay_period) references pay_period(start_date), -- fk_budget_period
  foreign key (issue_num) references issue(num), -- fk_budget_issue
  foreign key (voter) references github_users(login) -- fk_budget_voter
)
;
alter table budget_vote add column weight int;
ALTER TABLE budget_vote CONVERT TO CHARACTER SET utf8;


create table reward_vote (
  pay_period date not null,
  issue_num integer not null,
  voter varchar(64) not null,
  worker varchar(64) not null,
  percent integer not null,
  vote_time timestamp not null default current_timestamp,
  primary key(pay_period, issue_num, voter, worker),
  foreign key (pay_period) references pay_period(start_date), -- fk_reward_period
  foreign key (issue_num) references issue(num), -- fk_reward_issue
  foreign key (voter) references github_users(login), -- fk_reward_voter
  foreign key (worker) references github_users(login) -- fk_reward_worker
)
;

alter table reward_vote add column slash boolean;
alter table reward_vote add column weight int;
ALTER TABLE reward_vote CONVERT TO CHARACTER SET utf8;


CREATE TABLE `reward_fixed` (
  `issue_num` int(11) NOT NULL,
  `title` text NOT NULL,
  `worker` varchar(64) NOT NULL,
  `reward_usd` decimal(13, 2) not null,
  `percent_avg` double not null,
  `budget_usd` decimal(13, 2) not null,
  `voter_qty` int NOT NULL,
  `voters` mediumtext not null,
  `reward_provisional` double DEFAULT NULL,
  `budget_provisional` double DEFAULT NULL,
  `pay_period` date NOT NULL,
  `labels` mediumtext CHARACTER SET utf8,
  primary key(pay_period, issue_num, worker),
  foreign key (pay_period) references pay_period(start_date), -- fk_reward_period
  foreign key (issue_num) references issue(num), -- fk_reward_issue
  foreign key (worker) references github_users(login) -- fk_reward_worker
) ENGINE=InnoDB DEFAULT CHARSET=utf8
;

/* TODO: automate close of pay_period:

insert into reward_fixed select * from reward where reward_usd is not null;
*/

create table trust_cert (
        subject varchar(64) not null,
        voter varchar(64) not null,
        rating int not null,  -- TODO: check constraint: 1, 2, 3
        cert_time timestamp not null default current_timestamp,
        primary key(voter, subject),
        foreign key (voter) references github_users(login), -- fk_cert_voter
        foreign key (subject) references github_users(login) -- fk_cert_worker
        )
    ;
ALTER TABLE trust_cert CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;

ALTER DATABASE xataface CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
