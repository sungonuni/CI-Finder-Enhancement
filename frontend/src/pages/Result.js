import './App.css';
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import { Layout, Menu, Space, message} from 'antd';
import { Card, Checkbox, Col, Row } from 'antd';
import { Divider } from 'antd';
import { Descriptions } from 'antd';
import { Table } from 'antd';
import { Collapse } from 'antd';

import axios from 'axios';

import { IsBoolVarWithUnderbar } from './Util'

/**
 * To avoid the CORS issue, API address must be separated between dev mode and production mode.
 * Dev mode: /api/{API}
 * production mode: /{API}
 */
const PROXY = window.location.hostname === 'localhost' ? '/api' : '';
const DOWNLOADURL = `${PROXY}/Download`;

const { Header, Content, Footer } = Layout;
const { Panel } = Collapse;


/**
 * Check target tcl variable exists in all result B2Bs.
 * @param {string} tcl Name of target tcl
 * @param {string} tc Name of target test case
 * @param {Object} testData Entire result B2Bs data from backend server
 * @param {string} dataType boolean or string 
 * @returns {boolean}
 */
function isExistAllB2B(tcl, tc, testData, dataType) {
  for (let B2B of testData.info) {
    if (B2B.testCase[tc] !== undefined &&
      Object.keys(B2B.testCase[tc][dataType].match).includes(tcl) === false) {
      return false;
    }
  }
  return true;
}

/**
 * Make tcl variable checklist for filtering of result B2B list. 
 * @param {Object} testData Entire result B2Bs data from backend server
 * @param {Object} inputInfo Input information data
 * @param {Object} checkedTclObj Checked Tcl variables of App.js (Not separated between string variables and boolean variables)
 * @param {string} dataType boolean or string 
 * @returns {Object, Object} FilterChkListPerTc, GreyChkListPerTc 
 */
function makeFilterChkList(testData, inputInfo, checkedTclObj, dataType) {
  let FilterChkListPerTc = {};
  let GreyChkListPerTc = {};
  let tmpCheckedTclObj = {}

  for (let TC of Object.keys(inputInfo.tclData)) {
    FilterChkListPerTc[TC] = new Set();
    GreyChkListPerTc[TC] = new Set();
    tmpCheckedTclObj[TC] = new Set([...checkedTclObj[TC]]);
  }

  // FilterChkListPerTc: Tcl variables which may exist in some B2Bs or not. meaningful for filtering.
  for (let B2B of testData.info) {
    for (let TC of Object.keys(inputInfo.tclData)) {
      if (B2B.testCase[TC] !== undefined && Object.keys(B2B.testCase[TC][dataType]).length !== 0) {
        for (let TCL of Object.keys(B2B.testCase[TC][dataType].match)) {
          if (dataType === "boolean" && 
          IsBoolVarWithUnderbar(TCL) !== true &&
          B2B.testCase[TC][dataType].match[TCL] === true) {
            FilterChkListPerTc[TC].add(TCL);
          } else if (dataType === "string") {
            FilterChkListPerTc[TC].add(TCL);
          } else {
            continue;
          }
        }
      }
    }
  }

  // GreyChkListPerTc: Tcl variables which already exist in all result B2Bs, meaningless for filtering.
  for (let TC of Object.keys(inputInfo.tclData)){
    for (let TCL of FilterChkListPerTc[TC]) {
      if (isExistAllB2B(TCL, TC, testData, dataType) === true) {
        GreyChkListPerTc[TC].add(TCL) 
      }
    }
  }

  // FilterChkListPerTc = FilterChkListPerTc - GreyChkListPerTc
  // GreyChkListPerTc = GreyChkListPerTc - tmpCheckedTclObj
  for (let TC of Object.keys(inputInfo.tclData)) {
    FilterChkListPerTc[TC] = new Set([...FilterChkListPerTc[TC]].filter(x => !GreyChkListPerTc[TC].has(x)));
    FilterChkListPerTc[TC] = new Set([...FilterChkListPerTc[TC]].filter(x => !tmpCheckedTclObj[TC].has(x)));
    GreyChkListPerTc[TC] = new Set([...GreyChkListPerTc[TC]].filter(x => !tmpCheckedTclObj[TC].has(x)));
    
    FilterChkListPerTc[TC] = Array.from(FilterChkListPerTc[TC]);
    GreyChkListPerTc[TC] = Array.from(GreyChkListPerTc[TC]);
  }

  return [FilterChkListPerTc, GreyChkListPerTc];
}


// Init filtered List
/**
 * Initiate the filteredPerTC object.
 * filteredPerTC: Object to store all checked tcl variable per Test Case. 
 * @param {Array} inputSteTC List of input ste's test cases
 * @returns {Object}
 */
function initFilteredPerTC(inputSteTC){
  let filteredPerTC = {};
  for (let TC of inputSteTC){
    filteredPerTC[TC] = [];
  }
  return filteredPerTC;
}

/**
 * Add the test case key for checkedTclObj
 * @param {Object} checkedTclObj checked Tcl Varaibles per TC 
 * @param {Array} inputSteTC All test case list of input ste
 * @returns {Object}
 */
function AddKey2CheckedTclObj(checkedTclObj, inputSteTC){
  let keyCheckedTclObj = {};
  for (let TC of inputSteTC){
    if (!Object.keys(checkedTclObj).includes(TC)){
      keyCheckedTclObj[TC] = [];
    } else {
      keyCheckedTclObj[TC] = checkedTclObj[TC];
    }
  }
  return keyCheckedTclObj;
}

/**
 * Check whether each B2B has checked Tcl Variable or not.
 * @param {Object} B2B 
 * @param {Array} inputSteTC 
 * @param {Object} selectedPerTC 
 * @returns {Boolean}
 */
function isIncludeB2B(B2B, inputSteTC, selectedPerTC) {
  for (let TC of inputSteTC) {
    for (let TCL of selectedPerTC[TC]) {
      if (!((Object.keys(B2B.testCase[TC].boolean.match).includes(TCL) &&
        B2B.testCase[TC].boolean.match[TCL] === true) ||
        (Object.keys(B2B.testCase[TC].string.match).includes(TCL)))) {
        return false;
      }
    }
  }
  return true;
}

function findMatchedB2Bs(testData, inputSteTC, selectedPerTC){
  let DisplayedB2BList = [];
  for (let B2Bidx in testData.info){
    let B2B = testData.info[B2Bidx];
    if (isIncludeB2B(B2B, inputSteTC, selectedPerTC) === true) {
      DisplayedB2BList.push(B2Bidx);
    }
  }

  return DisplayedB2BList;
}

/**
 * Make result B2B list table data.
 * @param {Object} testData Entire result B2Bs data from backend server
 * @param {Array} resultB2BList List of index of Result B2Bs 
 * @returns {Object}
 */
function makeTableData(testData, resultB2BList) {
  let tableData = [];
  for (let B2Bidx of resultB2BList) {
    let row = {};
    row['key'] = B2Bidx; 
    row['name'] = testData.info[B2Bidx].name;
    row['score'] = testData.info[B2Bidx].score;
    tableData.push(row);
  }
  return tableData;
}


// Result page
function ShowResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [table, setTable] = useState(null);

  const testData = state.B2BListParams;
  const inputInfo = state.inputInfoParams;
  const checkedBoolTclObj = AddKey2CheckedTclObj(state.checkedBoolTclParams, Object.keys(inputInfo.tclData));
  const checkedStringTclObj = AddKey2CheckedTclObj(state.checkedStringTclParams, Object.keys(inputInfo.tclData));
  const [FilterBoolChkListPerTc, GreyBoolChkListPerTc] = makeFilterChkList(testData, inputInfo, checkedBoolTclObj, "boolean");
  const [FilterStringChkListPerTc, GreyStringChkListPerTc] = makeFilterChkList(testData, inputInfo, checkedStringTclObj, "string");

  const onClickLogo = (event) => {
    navigate(-2);
  };

  const bodyStyle = {
    maxHeight: '100%',
  };

  // Input test suite information
  /**
   * Show the input STE’s information.
   */
  const showInfo = () => {
    let input = {};
    let tcNameList = {};
    let isB2B = Boolean();
  
    input = inputInfo;

    tcNameList = Object.keys(input.tclData).map((tcName) => tcName+' ('+input.tclData[tcName].string.TestActivity+')');
    tcNameList.sort();

    return (
      <>
        <Descriptions.Item label="Name" span={2}>
          {input.name}
        </Descriptions.Item>
        <Descriptions.Item label="Number of test case">
          {tcNameList.length}
        </Descriptions.Item>
        <Descriptions.Item label="Name of test case" span={2}>
          {tcNameList.map((name, _) => (
            <Col key={name}>
              {name}
            </Col>
          ))}
        </Descriptions.Item>
        {isB2B && (
          <Descriptions.Item label="Score">
            {input.score}
          </Descriptions.Item>
        )}
      </>
    );
  };


  const inputSte = Object.keys(inputInfo.tclData);
  const filteredPerTC = initFilteredPerTC(inputSte);
  let tableData = {};
  

  useEffect(() => {
    tableData = makeTableData(testData, Array(testData.info.length).keys());
    setTable(tableData);
  }, []);


  // Show CheckBox Slot
  /**
   * Re-make the B2B list based on filter
   * @param {Array} TC 
   * @param {Array} checkedValues 
   */
  const onChangeFilter = (TC, checkedValues) => {
    filteredPerTC[TC] = checkedValues;
    
    tableData = makeTableData(testData, findMatchedB2Bs(testData, inputSte, filteredPerTC));
    setTable(tableData);
  };

  const showFilter = () => {
    let input = inputInfo;
    let inputTC = Object.keys(input.tclData);

    return (
      <div
        style={{ padding: '1% 2%' }}
      >
        {inputTC.map((TC, _) => (
          <>
            <Divider
              orientation="left"
              key={TC}
            >
              {TC}
            </Divider>
            <Checkbox.Group style={{ width: '100%' }} onChange={(e) => onChangeFilter(TC, e)}>
              <Row gutter={16}>
                <Divider
                  orientation="center"
                  key="Boolean"
                >
                  Boolean
                </Divider>
                {FilterBoolChkListPerTc[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox value={TCL}>{TCL}</Checkbox>
                  </Col>
                ))}
                {GreyBoolChkListPerTc[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox disabled>{TCL}</Checkbox>
                  </Col>
                ))}
                {checkedBoolTclObj[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox indeterminate disabled>{TCL}</Checkbox>
                  </Col>
                ))}
                <Divider
                  orientation="center"
                  key="String"
                >
                  String
                </Divider>
                {FilterStringChkListPerTc[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox value={TCL}>{TCL}</Checkbox>
                  </Col>
                ))}
                {GreyStringChkListPerTc[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox disabled>{TCL}</Checkbox>
                  </Col>
                ))}
                {checkedStringTclObj[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox indeterminate disabled>{TCL}</Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </>
        ))}
      </div>
    );
  }


  // Similar CI test suites
  /**
   * Call navigate() to move the pointer to Detail page.
   * - Parameter
   *  B2BList: Result B2B list data from server.
   *  inputInfo: Input STE data.
   *  B2B.key: Index of B2B.
   * @param {*} e 
   * @param {string} B2B 
   */
  const onClickDetail = (e, B2B) => {
    navigate(`/Result/${B2B.key}`, { 
      state: {
        B2BListParams: testData, 
        inputInfoParams: inputInfo,
      }});
  };

  /**
   * Call /Download API to the server with query parameter
   * - Parameter
   *  name: The name of B2B
   *  address: TAS address
   *  libraryId: TAS Library ID
   *  deleteSte: STE delete config
   * @param {*} e 
   * @param {string} B2B 
   */
  const onClickDownload = async(e, B2B) => {
    const hideMessage = message.loading(`Try to download the B2B`, 0);
    try{
      const res = await axios.post(DOWNLOADURL, null, {
        params: {
          name: testData.info[B2B.key].name,
          address : testData.info[B2B.key].TAS.address,
          libraryId: testData.info[B2B.key].TAS.libraryId,
          deleteSte: true
        },
        headers: {
          'Content-Type': 'application/json'
        },
        responseType: 'blob'
      }); 

      message.success(`Success to download!`);

      let url  = window.URL.createObjectURL(res.data);
      let a = document.createElement('a');
      a.href = url;
      a.download = testData.info[B2B.key].name+'.ste';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
    catch(e) {
      message.error(`cannot download ste file`);
    }
    finally {
      hideMessage();
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
    },
    {
      title: 'Score',
      dataIndex: 'score',
      defaultSortOrder: 'descend',
      sorter: (a, b) => a.score - b.score,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, B2B) => (
        <Space size="middle">
          <a onClick={(e) => onClickDetail(e, B2B)}>Detail</a>
          {testData.info[B2B.key].status === "1" && // Check B2B can be downloaded.
            <a onClick={(e) => onClickDownload(e, B2B)}>Download</a>
          }
        </Space>
      ),
    },
  ];

  return (
    <>
      <Layout className="layout">
        <Header
          style={{ backgroundColor: "#2185D0" }}
        >
          <div className="logo" onClick={onClickLogo}/>
          <Menu
            style={{ backgroundColor: "#2185D0", color: "#D0D0D0" }}
            mode="horizontal"
            defaultSelectedKeys={['1']}
          />
        </Header>
        <Layout style={{ minHeight: '80vh' }}>
          <Content style={{ padding: '1% 3%' }}>
            <div className="site-card-wrapper" style={{ padding: '2% 5%' }}>
              <>
                <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                  <Card
                    style={{
                      width: '100%',
                      height: 300,
                      maxHeight: 300,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                      <Descriptions title="Input test suite information" bordered>
                        {showInfo()}
                      </Descriptions>
                    </Space>
                  </Card>
                  <Collapse>
                    <Panel
                      header="Filter"
                      key="1"
                    >
                      <Space
                        direction="vertical"
                        size="middle"
                        style={{
                          display: 'flex',
                        }}
                      >
                        {showFilter()}
                      </Space>
                    </Panel>
                  </Collapse>
                  <Card
                    title="Similar CI test suites"
                    style={{
                      width: '100%',
                      height: 800,
                      maxHeight: 800,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    {table && (
                      <Table columns={columns} dataSource={table} />
                    )}
                  </Card>
                </Space>
              </>
            </div>
          </Content>
        </Layout>
        <Footer style={{ textAlign: 'center' }}>©2023 Spirent Communications, Inc. All rights reserved.</Footer>
      </Layout>
    </>
  );
}

export default ShowResult;