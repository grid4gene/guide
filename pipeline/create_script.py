import os, sys, stat

sp_name = os.environ["sp_name"]
dir_vcf = os.environ["dir_vcf"]
dir_analyzed_sample = os.environ["dir_analyzed_sample"]
dir_bin = os.environ["dir_bin"]
hg19=os.environ["hg19"]
num_split=5
num_nct="3"


bqsr_str1 = "java -jar " + dir_bin + "/GenomeAnalysisTK.jar  -nct " + num_nct + " -T BaseRecalibrator -l INFO  -R " + hg19 +  " -knownSites "+ dir_vcf +"/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -knownSites " + dir_vcf + "/1000G_phase1.indels.hg19.sites.vcf  -I " + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned.bam -o "
bqsr_str2 = dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned."
bqsr_str3 = ".grp "

merge_bqsr="java -cp " + dir_bin + "/GenomeAnalysisTK.jar org.broadinstitute.gatk.tools.GatherBqsrReports O=" + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned.grp "

apply_str1="java -jar " + dir_bin + "/GenomeAnalysisTK.jar -nct " + num_nct + " -T PrintReads -R " + hg19 +  " -I " + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned.bam -BQSR " + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned.grp -o "
apply_str2= dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned-recal." 
apply_str3=".bam " 

merge_bam="java -jar " + dir_bin + "/picard.jar GatherBamFiles CREATE_INDEX=true CREATE_MD5_FILE=true OUTPUT=" + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned-recal.bam "
merge_bam_str1=dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned-recal."
merge_bam_str2=".bam"

#time bash -c "taskset -c 0-17 java -jar $dir_bin/GenomeAnalysisTK.jar -nct 4 -T HaplotypeCaller -R $hg19 -stand_call_conf 10.0 -minPruning 3  -mbq 5  -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -o $dir_analyzed_sample/$sp_name-Haploy-SNP-INDLE.vcf"
htc_str1 = "java -jar " + dir_bin + "/GenomeAnalysisTK.jar -nct " + num_nct + " -T HaplotypeCaller -R " + hg19 +  " -stand_call_conf 10.0 -minPruning 3 -mbq 5 -I " + dir_analyzed_sample + "/" + sp_name + "-ali-sorted-RG-rmdup-realigned-recal.bam -o "
htc_str2 = dir_analyzed_sample + "/" + sp_name + "-Haploy-SNP-INDLE."
htc_str3 = ".vcf "

merge_htc="java -jar " + dir_bin + "/picard.jar MergeVcfs OUTPUT=" + dir_analyzed_sample + "/" + sp_name + "-Haploy-SNP-INDLE.vcf "
merge_htc_str1=dir_analyzed_sample + "/" + sp_name + "-Haploy-SNP-INDLE."
merge_htc_str2=".vcf "

#create script directory
import os, sys
if os.path.isdir("./script"):
    pass
else:
    os.mkdir("./script", 0755)


with open("/home/test/WGS_pipeline/reference/hg19.dict", "r") as ref_dict_file:
    sequence_tuple_list = []
    longest_sequence = 0
    for line in ref_dict_file:
        if line.startswith("@SQ"):
            line_split = line.split("\t")
            # (Sequence_Name, Sequence_Length)
            sequence_tuple_list.append((line_split[1].split("SN:")[1], int(line_split[2].split("LN:")[1])))
    #longest_sequence = sorted(sequence_tuple_list, key=lambda x: x[1], reverse=True)[0][1]
    seq_len = [line[1] for line in sequence_tuple_list]
    split_len = sum(seq_len)/num_split
    
    #total_sequence = sum(sequence_tuple_list[:][])
# We are adding this to the intervals because hg38 has contigs named with embedded colons (:) and a bug in
# some versions of GATK strips off the last element after a colon, so we add this as a sacrificial element.
#hg38_protection_tag = ":1+"
# initialize the tsv string with the first sequence
#tsv_string = sequence_tuple_list[0][0] + hg38_protection_tag
tsv_string = "-L " + sequence_tuple_list[0][0]
temp_size = sequence_tuple_list[0][1]
for sequence_tuple in sequence_tuple_list[1:]:
    #if temp_size + sequence_tuple[1] <= longest_sequence:
    if temp_size + sequence_tuple[1] <= split_len:
        temp_size += sequence_tuple[1]
        #tsv_string += "\t" + sequence_tuple[0] + hg38_protection_tag
        tsv_string += " -L " + sequence_tuple[0]
    else:
        #tsv_string += "\n" + sequence_tuple[0] + hg38_protection_tag
        tsv_string += "\n-L " + sequence_tuple[0]
        temp_size = sequence_tuple[1]
#tsv_string += "\n"

#create the bqsr.sh
count = 0
cli=""
bqsr_list = tsv_string.splitlines()
lenght = len(bqsr_list)
while count < lenght :
    cli += bqsr_str1 + bqsr_str2 + str(count) + bqsr_str3 + bqsr_list[count] + "\n"
    count += 1

with open("./script/bqsr.sh", "w") as bqsr_file:
  bqsr_file.write(cli)
  bqsr_file.close()

count=0
cli=merge_bqsr
lenght = len(bqsr_list)
while count < lenght :
    cli += "I=" + bqsr_str2 + str(count) + bqsr_str3 + " "
    count += 1

cli += "\n"
with open("./script/merge_bqsr.sh", "w") as merge_bqsr_file:
  merge_bqsr_file.write(cli)
  merge_bqsr_file.close()



count = 0
cli=""
htc_list = tsv_string.splitlines()
lenght = len(htc_list)
while count < lenght :
    cli += htc_str1 + htc_str2 + str(count) + htc_str3 + htc_list[count] + "\n"
    count += 1

with open("./script/htc.sh", "w") as htc_file:
  htc_file.write(cli)
  htc_file.close()

count=0
cli=merge_htc
lenght = len(htc_list)
while count < lenght :    
    cli += "INPUT=" + merge_htc_str1 + str(count) + merge_htc_str2 + " "    
    count += 1

cli += "\n"
with open("./script/merge_htc.sh", "w") as merge_htc_file:
  merge_htc_file.write(cli)
  merge_htc_file.close()



# add the unmapped sequences as a separate line to ensure that they are recalibrated as well
#with open("sequence_grouping.txt", "w") as tsv_file:
#  tsv_file.write(tsv_string)
#  tsv_file.close()

tsv_string += ' -L ' + "unmapped\n"
#with open("sequence_grouping_with_unmapped.txt", "w") as tsv_file_with_unmapped:
#  tsv_file_with_unmapped.write(tsv_string)
#  tsv_file_with_unmapped.close()

#create the apply_bqsr.sh
count = 0
cli=""
bqsr_list = tsv_string.splitlines()
lenght = len(bqsr_list)
while count < lenght :
    cli += apply_str1 + apply_str2 + str(count) + apply_str3 + bqsr_list[count] + "\n"
    count += 1

with open("./script/apply.sh", "w") as apply_file:
  apply_file.write(cli)
  apply_file.close()

#merge bam
count=0
cli=merge_bam
lenght = len(bqsr_list)
while count < lenght :
    cli += "INPUT=" + merge_bam_str1 + str(count) + merge_bam_str2 + " "
    count += 1

cli += "\n"
with open("./script/merge_bam.sh", "w") as merge_bam_file:
  merge_bam_file.write(cli)
  merge_bam_file.close()


#set the execute for the shell
os.chmod("./script/bqsr.sh", stat.S_IEXEC)
os.chmod("./script/apply.sh", stat.S_IEXEC)
os.chmod("./script/merge_bqsr.sh", stat.S_IEXEC)
os.chmod("./script/merge_bam.sh", stat.S_IEXEC)
os.chmod("./script/htc.sh", stat.S_IEXEC)
os.chmod("./script/merge_htc.sh", stat.S_IEXEC)