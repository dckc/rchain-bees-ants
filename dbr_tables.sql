drop table if exists trust_cert;
drop table if exists invoice_info;
drop table if exists reward_vote;
drop table if exists budget_vote;
drop table if exists github_users;
drop table if exists admin_settings;
drop table if exists pay_period;

drop table if exists issue;
create table issue (
  num integer primary key,
  title varchar(1024) not null,
  updatedAt timestamp,
  `state` varchar(32) not null,
  repo varchar(1024) not null
)
;


create table pay_period (
        start_date date primary key,
        end_date date not null,
    -- Rchain RHOC Volume Weighted Average
    --    https://docs.google.com/spreadsheets/d/1XlbJchQhIVmn57pe8eeJ9QctKIWk5KLEToRyCGu2TgM/edit#gid=356502091
    -- update pay_period set usd_per_rhoc=1.615;
        usd_per_rhoc decimal(12, 3)
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
  `login` varchar(22) NOT NULL,
  `followers` bigint(20) DEFAULT NULL,
  `name` varchar(31) DEFAULT NULL,
  `location` varchar(39) DEFAULT NULL,
  `email` varchar(30) DEFAULT NULL,
  `bio` varchar(161) DEFAULT NULL,
  `websiteUrl` varchar(42) DEFAULT NULL,
  `avatarUrl` varchar(57) DEFAULT NULL,
  `permission` varchar(9) DEFAULT NULL,
  `createdAt` datetime DEFAULT NULL,
  `session_token` varchar(64) DEFAULT NULL,
  `verified_coop` bigint(20) unsigned DEFAULT NULL,
  PRIMARY KEY (`login`),
  KEY `ix_github_users_login` (`login`)
)
;


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


create table invoice_info (
  pay_period date not null,
  worker varchar(64) not null,
  name varchar(128) not null,
  rhoc_wallet varchar(128),
  primary key(pay_period, worker),
  foreign key (worker) references github_users(login), -- fk_invoice_worker
  foreign key (pay_period) references pay_period(start_date) -- fk_invoice_period
  )
;


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
