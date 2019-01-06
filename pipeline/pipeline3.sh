#!/bin/bash

set -x
ulimit -n 102400

#input file
R1='TEST/FASTQ_LAURA/412_1.fastq.gz'
R2='TEST/FASTQ_LAURA/412_1.fastq.gz'
#reference file
hg19='reference/hg19.fasta'
dir_vcf='reference'
threads=4
sp_name='pipe3'
dir_analyzed_sample='TEST/output'
dir_bin='/home/opt/tools'
bed='reference/Agilent_S06588914_Covered.chr.bed'

time ${dir_bin}/bwa mem  -t $threads  $hg19  $R1 $R2 | ${dir_bin}/samtools view -S -b > $dir_analyzed_sample/$sp_name-bwa.bam

# filter reads un-mapped reads and sort bam file
time ${dir_bin}/samtools view -h  -F 4 $dir_analyzed_sample/$sp_name-bwa.bam | ${dir_bin}/samtools view -Sb > $dir_analyzed_sample/$sp_name-ali.bam

# Sorting BAM
time ${dir_bin}/samtools sort $dir_analyzed_sample/$sp_name-ali.bam  -o $dir_analyzed_sample/$sp_name-ali-sorted.bam

# Add ReadGroup
time java -jar ${dir_bin}/picard.jar AddOrReplaceReadGroups  I=$dir_analyzed_sample/$sp_name-ali-sorted.bam  O=$dir_analyzed_sample/$sp_name-ali-sorted-RG.bam  RGSM=$sp_name RGLB=project RGPL=illumina RGID=none RGPU=none VALIDATION_STRINGENCY=LENIENT

# Remove duplicates
time java -jar ${dir_bin}/picard.jar MarkDuplicates  REMOVE_DUPLICATES=TRUE CREATE_INDEX=TRUE VALIDATION_STRINGENCY=LENIENT MAX_RECORDS_IN_RAM=4000000 ASSUME_SORTED=TRUE I=$dir_analyzed_sample/$sp_name-ali-sorted-RG.bam  O=$dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam  METRICS_FILE=$dir_analyzed_sample/$sp_name-pacard.metrics

# index BAM
time ${dir_bin}/samtools index $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam

# RealignerTargetCreator
time java -jar $dir_bin/GenomeAnalysisTK.jar -nt $threads -T RealignerTargetCreator -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf  -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf  -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam.list

# IndelRealigner
time java -jar $dir_bin/GenomeAnalysisTK.jar  -T IndelRealigner -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam -targetIntervals $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam.list -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.bam

#BaseRecalibrator
time java -jar $dir_bin/GenomeAnalysisTK.jar  -nct $threads -T BaseRecalibrator -l INFO  -R $hg19   -knownSites $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -knownSites $dir_vcf/1000G_phase1.indels.hg19.sites.vcf  -I  $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.bam -o  $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.grp

# GATK PrintReads
time java -jar $dir_bin/GenomeAnalysisTK.jar -nct $threads -T PrintReads -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.bam -BQSR $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.grp -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal-0.bam

# Filter mapping quality <10
time ${dir_bin}/samtools view -h  -q 10 $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal-0.bam |${dir_bin}/samtools view -h -Sb > $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam

# index BAM
time  ${dir_bin}/samtools index $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam

# GATK UnifiedGenotyper
time java -jar $dir_bin/GenomeAnalysisTK.jar -nt $threads -T UnifiedGenotyper -R $hg19  -L $bed  -metrics $dir_analyzed_sample/$sp_name-snps.metrics -stand_call_conf 10.0 -dcov 20000 -glm BOTH -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -o $dir_analyzed_sample/$sp_name-Unified-SNP-INDLE.vcf

#GARK HaplotypeCaller
time java -jar $dir_bin/GenomeAnalysisTK.jar -nct  $threads -T HaplotypeCaller -R $hg19 -L $bed -stand_call_conf 10.0 -minPruning 3  -mbq 5  -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -o $dir_analyzed_sample/$sp_name-Haploy-SNP-INDLE.vcf
