/* 
- Long input: 1024 symbols
- Short input: 30 symbols
*/

export interface Field {
    type: 'field';
    index: string;
    header: string;
    input_length: string; // short / long
    input: string | number;
    display: boolean;
}