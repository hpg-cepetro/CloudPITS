-- The MIT License (MIT)
--
-- Copyright (c) 2019 Nicholas Torres Okita <nicholas.okita@ggaunicamp.com>
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy
-- of this software and associated documentation files (the "Software"), to
-- deal in the Software without restriction, including without limitation the
-- rights to use, copy, modify, merge, publish, distribute, sublicense,
-- and/or sell copies of the Software, and to permit persons to whom the
-- Software is furnished to do so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in
-- all copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
-- FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
-- THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
-- LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
-- FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
-- IN THE SOFTWARE.
--
-- MySQL script to create the database for performance reports

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema experimentos
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema experimentos
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `experimentos` DEFAULT CHARACTER SET utf8 ;
USE `experimentos` ;

-- -----------------------------------------------------
-- Table `experimentos`.`data`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`data` (
  `iddata` INT(11) NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(45) NULL DEFAULT NULL,
  `hash` VARCHAR(45) NULL DEFAULT NULL,
  PRIMARY KEY (`iddata`))
ENGINE = InnoDB
AUTO_INCREMENT = 13
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `experimentos`.`instance`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`instance` (
  `name` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`name`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `experimentos`.`parameters`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`parameters` (
  `idparameters` INT(11) NOT NULL AUTO_INCREMENT,
  `aph` FLOAT NULL DEFAULT NULL,
  `apm` FLOAT NULL DEFAULT NULL,
  `window` DOUBLE NULL DEFAULT NULL,
  `np` FLOAT NULL DEFAULT NULL,
  `gens` FLOAT NULL DEFAULT NULL,
  PRIMARY KEY (`idparameters`))
ENGINE = InnoDB
AUTO_INCREMENT = 49
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `experimentos`.`experiment`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`experiment` (
  `idperformance` INT(11) NOT NULL AUTO_INCREMENT,
  `data_iddata` INT(11) NOT NULL,
  `parameters_idparameters` INT(11) NOT NULL,
  `instance_name` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`idperformance`),
  INDEX `fk_performance_data1_idx` (`data_iddata` ASC) VISIBLE,
  INDEX `fk_performance_parameters1_idx` (`parameters_idparameters` ASC) VISIBLE,
  INDEX `fk_performance_instance1_idx` (`instance_name` ASC) VISIBLE,
  CONSTRAINT `fk_performance_data1`
    FOREIGN KEY (`data_iddata`)
    REFERENCES `experimentos`.`data` (`iddata`),
  CONSTRAINT `fk_performance_instance1`
    FOREIGN KEY (`instance_name`)
    REFERENCES `experimentos`.`instance` (`name`),
  CONSTRAINT `fk_performance_parameters1`
    FOREIGN KEY (`parameters_idparameters`)
    REFERENCES `experimentos`.`parameters` (`idparameters`))
ENGINE = InnoDB
AUTO_INCREMENT = 5731
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `experimentos`.`interpols`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`interpols` (
  `idinterpols` INT(11) NOT NULL AUTO_INCREMENT,
  `parameters_idparameters` INT(11) NOT NULL,
  `data_iddata` INT(11) NOT NULL,
  `interpols` FLOAT NULL DEFAULT NULL,
  `datetime` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`idinterpols`),
  INDEX `fk_interpols_parameters1_idx` (`parameters_idparameters` ASC) VISIBLE,
  INDEX `fk_interpols_data1_idx` (`data_iddata` ASC) VISIBLE,
  CONSTRAINT `fk_interpols_data1`
    FOREIGN KEY (`data_iddata`)
    REFERENCES `experimentos`.`data` (`iddata`),
  CONSTRAINT `fk_interpols_parameters1`
    FOREIGN KEY (`parameters_idparameters`)
    REFERENCES `experimentos`.`parameters` (`idparameters`))
ENGINE = InnoDB
AUTO_INCREMENT = 71
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `experimentos`.`interpsec`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `experimentos`.`interpsec` (
  `idinterpsec` INT(11) NOT NULL AUTO_INCREMENT,
  `interpsec` FLOAT NULL DEFAULT NULL,
  `experiment_idperformance` INT(11) NOT NULL,
  `creationDate` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`idinterpsec`),
  INDEX `fk_interpsec_experiment1_idx` (`experiment_idperformance` ASC) VISIBLE,
  CONSTRAINT `fk_interpsec_experiment1`
    FOREIGN KEY (`experiment_idperformance`)
    REFERENCES `experimentos`.`experiment` (`idperformance`))
ENGINE = InnoDB
AUTO_INCREMENT = 45971
DEFAULT CHARACTER SET = utf8;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
